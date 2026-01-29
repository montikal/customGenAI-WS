import chromadb
from chromadb.utils import embedding_functions

class ChromaStore:
    def __init__(self, persist_dir="./chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

    def get_collection(self, name: str):
        return self.client.get_or_create_collection(
            name=name,
            embedding_function=self.embedder
        )

    def upsert_chunks(self, col, doc_id: str, chunks):
        ids = [c["id"] for c in chunks]
        docs = [c["text"] for c in chunks]
        metas = [{"doc_id": doc_id, "page_start": c["page_start"], "page_end": c["page_end"]} for c in chunks]
        col.upsert(ids=ids, documents=docs, metadatas=metas)

    def query(self, col, question: str, k=15):
        try:
            return col.query(
                query_texts=[question],
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )
        except ValueError:
            # fallback: no include
            return col.query(query_texts=[question], n_results=k)
