from __future__ import annotations

from .tools.search import semantic_search
from .models import Document


def retrieve_baseline(corpus: dict[str, Document], question: str, top_k: int = 3) -> list[dict]:
    return semantic_search(corpus, question, limit=top_k)


def build_baseline_context(corpus: dict[str, Document], question: str, top_k: int = 3) -> str:
    hits = retrieve_baseline(corpus, question, top_k)
    blocks = []
    for hit in hits:
        doc = corpus[hit["id"]]
        blocks.append(f"# {doc.title} ({doc.id})\n{doc.body}")
    return "\n\n---\n\n".join(blocks)
