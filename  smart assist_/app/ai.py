import re
from collections import Counter

KEYWORDS = {
    "food": ["food", "hungry", "meal", "eat", "rice", "groceries", "bread", "starving"],
    "shelter": ["shelter", "homeless", "sleep", "roof", "street", "stay", "blanket", "house"],
    "medical": ["medical", "hospital", "injury", "injured", "medicine", "doctor", "bleeding", "sick", "ambulance", "pain"],
}
URGENT_TERMS = ["bleeding", "unconscious", "suicide", "violence", "abuse", "emergency", "ambulance", "cannot breathe", "severe pain", "child alone"]

def classify_need(text: str) -> str:
    normalized = text.lower()
    scores = {category: sum(1 for word in words if re.search(r"\b" + re.escape(word) + r"\b", normalized)) for category, words in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "other"

def assess_urgency(text: str) -> str:
    normalized = text.lower()
    return "urgent_review" if any(term in normalized for term in URGENT_TERMS) else "normal"

def summarize(text: str, max_words: int = 28) -> str:
    clean = " ".join(text.split())
    words = clean.split(" ")
    if len(words) <= max_words:
        return clean
    return " ".join(words[:max_words]).rstrip(".,;:") + "…"

def duplicate_candidates(description: str, cases: list, threshold: float = 0.55) -> list:
    """Simple token-Jaccard flagging. Similarity is a review aid, not proof of a duplicate."""
    def tokens(s):
        return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 2}
    target = tokens(description)
    found = []
    for case in cases:
        other = tokens(case.description)
        similarity = len(target & other) / max(1, len(target | other))
        if similarity >= threshold:
            found.append({"case_code": case.case_code, "similarity": round(similarity, 2), "status": case.status})
    return sorted(found, key=lambda x: x["similarity"], reverse=True)
