import re
from typing import List, Dict, Tuple

BOILERPLATE_PATTERNS = [
    r"\bcopyright\b",
    r"\ball rights reserved\b",
    r"\bno part of this\b",
    r"\bdisclaimer\b",
    r"\btrademark\b",
    r"\babb\b.*\b(copyright|all rights reserved)\b",
]

def is_boilerplate(text: str) -> bool:
    t = (text or "").strip().lower()
    if len(t) < 250:  # too short => likely header/footer or noise
        return True
    # too little alphabetic content => tables/garbage
    alpha = sum(ch.isalpha() for ch in t)
    if alpha / max(len(t), 1) < 0.55:
        return True
    for pat in BOILERPLATE_PATTERNS:
        if re.search(pat, t):
            return True
    return False

def keyword_set(question: str) -> set:
    # simple keyword extractor; good enough for MVP
    words = re.findall(r"[a-zA-Z]{3,}", question.lower())
    stop = {"what", "when", "where", "which", "who", "whom", "how", "why",
            "the", "and", "for", "with", "from", "this", "that", "into", "your"}
    return {w for w in words if w not in stop}

def has_keyword_overlap(question: str, chunk_text: str, min_hits: int = 1) -> bool:
    qk = keyword_set(question)
    if not qk:
        return True
    t = (chunk_text or "").lower()
    hits = sum(1 for w in qk if w in t)
    return hits >= min_hits

def build_answer_prompt(question: str, evidence_chunks):
    ctx_lines = []
    for i, ch in enumerate(evidence_chunks, 1):
        snippet = ch["text"][:900]  # prevent tokenizer truncation
        ctx_lines.append(
            f"Chunk {i} (id={ch['id']}, pages={ch['page_start']}-{ch['page_end']}):\n{snippet}"
        )
    context_block = "\n\n".join(ctx_lines)

    return f"""You are a SOP assistant. Answer ONLY using the context below.
If the answer is not in the context, say: I don't know.

Write a helpful answer in 3–8 bullet points.
If the question is asking "how to", provide step-by-step instructions.
Cite evidence in each bullet using (chunk_id, page).

CONTEXT:
{context_block}

QUESTION:
{question}

ANSWER:"""
