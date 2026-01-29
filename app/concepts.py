from typing import List, Dict

def extract_concepts_flan(llm, chunk_text: str) -> List[Dict]:
    """
    Extract lightweight concepts (keywords) from a chunk.
    MVP: simple keyword-style concepts, not deep relations.
    """
    prompt = f"""Extract up to 8 important terms (nouns or short noun phrases)
from the SOP text below.

Rules:
- Do NOT explain
- Do NOT add new information
- Output a comma-separated list only

Text:
{chunk_text}

Terms:"""

    output = llm.generate(prompt, max_new_tokens=60)

    terms = []
    for t in output.split(","):
        t = t.strip().lower()
        if len(t) > 2:
            terms.append({"name": t, "score": 1.0})

    return terms[:8]
