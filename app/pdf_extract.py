import fitz  # pymupdf

def extract_pages(pdf_path: str):
    doc = fitz.open(pdf_path)
    pages = []
    for i in range(len(doc)):
        text = doc[i].get_text("text") or ""
        pages.append({"page": i + 1, "text": text})
    return pages
