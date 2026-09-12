from __future__ import annotations

import os
from anthropic import Anthropic

from .tools.search import semantic_search
from .models import Document


def retrieve_baseline(corpus: dict[str, Document], question: str, top_k: int = 3) -> list[dict]:
    return semantic_search(corpus, question, limit=top_k)


def build_baseline_context(corpus: dict[str, Document], question: str, top_k: int = 3) -> tuple[str, list[dict]]:
    hits = retrieve_baseline(corpus, question, top_k)
    blocks = []
    for hit in hits:
        doc = corpus[hit["id"]]
        blocks.append(
            f"# {doc.title} ({doc.id})\n"
            f"published_at={doc.published_at}\n"
            f"valid_from={doc.valid_from}\n"
            f"valid_to={doc.valid_to}\n\n"
            f"{doc.body}"
        )
    return "\n\n---\n\n".join(blocks), hits


def answer_baseline(corpus: dict[str, Document], question: str, query_date=None, top_k: int = 3) -> dict:
    """Naive one-shot RAG baseline: top-k retrieval once, then answer once.

    Intentionally no temporal resolution, no reference following, no iterative search.
    This is the control condition for the demo, not a strawman hidden behind worse data.
    """
    context, hits = build_baseline_context(corpus, question, top_k)
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    date_text = query_date.isoformat() if query_date else "not supplied"

    response = client.messages.create(
        model=model,
        max_tokens=600,
        temperature=0,
        system=(
            "Answer the user's question using only the retrieved context. "
            "Be concise and cite document ids in parentheses. If the context appears sufficient, answer directly."
        ),
        messages=[
            {
                "role": "user",
                "content": f"Query date: {date_text}\nQuestion: {question}\n\nRetrieved context:\n{context}",
            }
        ],
    )
    text = "\n".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()
    return {
        "answer": text,
        "hits": hits,
        "model": model,
        "mode": "one-shot-top-k",
    }
