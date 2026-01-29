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
    res = chroma.query(col, req.question, k=15)
    retrieved_ids = res["ids"][0]
    retrieved_docs = res["documents"][0]
    retrieved_meta = res["metadatas"][0]

    # pack as chunks
    top_chunks = []
    for cid, text, meta in zip(retrieved_ids, retrieved_docs, retrieved_meta):
        top_chunks.append({"id": cid, "text": text, "page_start": meta.get("page_start"), "page_end": meta.get("page_end")})

    # 2) graph expand (optional): pull more chunks connected by concepts
    expanded = neo.expand_from_chunk_ids(req.doc_id, retrieved_ids, limit_chunks=12)

    # merge evidence (dedupe by id)
    seen = set()
    evidence = []
    for ch in top_chunks + expanded:
        if ch["id"] not in seen:
            seen.add(ch["id"])
            evidence.append(ch)

    evidence = evidence[:8]  # keep prompt small old value-12
            
    for ch in evidence:
        print(ch["id"], len(ch["text"]))

    prompt = build_answer_prompt(req.question, evidence)
    answer = llm.generate(prompt, max_new_tokens=200)

    return {"answer": answer, "evidence": [{"id": e["id"], "page_start": e["page_start"]} for e in evidence]}


@app.get("/health/chroma")
def chroma_health():
    col = chroma.get_collection("test_health")
    col.upsert(ids=["1"], documents=["hello"], metadatas=[{"a": 1}])
    res = col.query(query_texts=["hello"], n_results=1)
    return {"ok": True, "keys": list(res.keys())}