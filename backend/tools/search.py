from __future__ import annotations

import math
import re
from collections import Counter
from ..models import Document

TOKEN_RE = re.compile(r"[A-Za-z0-9_-]+")


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def _cosine(a: Counter, b: Counter) -> float:
    keys = set(a) | set(b)
    dot = sum(a[k] * b[k] for k in keys)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def semantic_search(corpus: dict[str, Document], query: str, limit: int = 5) -> list[dict]:
    """Hackathon-local lexical stand-in for embeddings.

    Search hits expose explicit dependency edges so the agent can follow authoritative
    references instead of repeatedly reformulating broad searches.
    """
    q = Counter(_tokens(query))
    scored = []
    for doc in corpus.values():
        text = f"{doc.title}\n{' '.join(doc.domains)}\n{doc.body}"
        score = _cosine(q, Counter(_tokens(text)))
        scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "id": d.id,
            "title": d.title,
            "score": round(score, 4),
            "references": list(d.references),
        }
        for score, d in scored[:limit]
    ]


def keyword_search(corpus: dict[str, Document], query: str, limit: int = 5) -> list[dict]:
    terms = set(_tokens(query))
    scored = []
    for doc in corpus.values():
        hay = _tokens(f"{doc.title} {' '.join(doc.domains)} {doc.body}")
        overlap = sum(1 for t in hay if t in terms)
        scored.append((overlap, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "id": d.id,
            "title": d.title,
            "matches": score,
            "references": list(d.references),
        }
        for score, d in scored[:limit]
        if score > 0
    ]
