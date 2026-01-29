from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
import uuid, os
from fastapi.staticfiles import StaticFiles

from app.pdf_extract import extract_pages
from app.chunking import chunk_pages
from app.chroma_store import ChromaStore
from app.neo4j_store import Neo4jStore
from app.llm_flan import FlanLLM
from app.graphrag import build_answer_prompt
from app.concepts import extract_concepts_flan
from pathlib import Path
from app.graphrag import is_boilerplate, has_keyword_overlap


app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
app.mount( 
    "/ui",
    StaticFiles(directory=BASE_DIR / "static", html=True),
    name="ui"
)


# app.mount("/", StaticFiles(directory="static", html=True), name="static")


chroma = ChromaStore(persist_dir="./chroma_db")
llm = FlanLLM("google/flan-t5-base")
neo = Neo4jStore(uri="bolt://localhost:7687", user="neo4j", password="your_password")

class ChatReq(BaseModel):
    doc_id: str
    question: str

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    doc_id = str(uuid.uuid4())
    os.makedirs("./uploads", exist_ok=True)
    pdf_path = f"./uploads/{doc_id}_{file.filename}"
    with open(pdf_path, "wb") as f:
        f.write(await file.read())

    pages = extract_pages(pdf_path)
    chunks = chunk_pages(pages)

    # Chroma
    col = chroma.get_collection(f"doc_{doc_id}")
    chroma.upsert_chunks(col, doc_id, chunks)

    # Neo4j
    neo.upsert_document(doc_id, file.filename)
    neo.upsert_chunks(doc_id, chunks)

    # Concepts (optional initially — can be slow)
    for c in chunks[:50]:  # MVP: limit first 50 chunks; later do async/background
        concepts = extract_concepts_flan(llm, c["text"])
        neo.link_concepts(c["id"], concepts)

    return {"doc_id": doc_id, "chunks": len(chunks), "filename": file.filename}

@app.post("/chat")
def chat(req: ChatReq):
    col = chroma.get_collection(f"doc_{req.doc_id}")

    # 1) vector retrieve
    res = col.query(
        query_texts=[req.question],
        n_results=20,  # raise recall a bit
        include=["documents", "metadatas", "distances"]
    )

    ids = res.get("ids", [[]])[0]
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]

    # Pack chunks with distances
    retrieved = []
    for cid, text, meta, dist in zip(ids, docs, metas, dists):
        retrieved.append({
            "id": cid,
            "text": text,
            "page_start": meta.get("page_start"),
            "page_end": meta.get("page_end"),
            "distance": dist
        })

    # 2) Minimal sanity filter: remove boilerplate/noise
    filtered = [c for c in retrieved if not is_boilerplate(c["text"])]

    # 3) Optional: require some keyword overlap with the question
    filtered2 = [c for c in filtered if has_keyword_overlap(req.question, c["text"], min_hits=1)]

    # Choose evidence set (fallback if overlap filter too strict)
    evidence = filtered2[:8] or filtered[:8]

    # 4) Weak retrieval guard: if still empty or best distance is too high => don't answer
    if not evidence:
        return {
            "answer": "I don't know. I couldn't find relevant content in the document for this question.",
            "evidence": []
        }

    best_dist = min(c["distance"] for c in evidence if c.get("distance") is not None)
    # NOTE: threshold depends on embedding model & metric. Start conservative.
    DIST_THRESHOLD = 0.65
    if best_dist > DIST_THRESHOLD:
        return {
            "answer": "I don't know. The retrieved context doesn't look relevant enough to answer reliably.",
            "evidence": [{"id": e["id"], "page_start": e["page_start"], "distance": e["distance"]} for e in evidence]
        }

    # 5) Build prompt from PDF chunks (this is the key: answer comes from text chunks)
    prompt = build_answer_prompt(req.question, evidence)
    answer = llm.generate(prompt, max_new_tokens=220)

    return {
        "answer": answer,
        "evidence": [{"id": e["id"], "page_start": e["page_start"], "distance": e["distance"]} for e in evidence]
    }


@app.get("/health/chroma")
def chroma_health():
    col = chroma.get_collection("test_health")
    col.upsert(ids=["1"], documents=["hello"], metadatas=[{"a": 1}])
    res = col.query(query_texts=["hello"], n_results=1)
    return {"ok": True, "keys": list(res.keys())}