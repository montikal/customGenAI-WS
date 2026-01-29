import uuid

def chunk_pages(pages, chunk_size=1100, overlap=200):
    chunks = []
    for p in pages:
        text = " ".join(p["text"].split())
        if not text:
            continue
        start = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            chunk_text = text[start:end]
            chunks.append({
                "id": str(uuid.uuid4()),
                "page_start": p["page"],
                "page_end": p["page"],
                "text": chunk_text,
                "text_preview": chunk_text[:200]
            })
            if end == len(text):
                break
            start = max(0, end - overlap)
    return chunks
