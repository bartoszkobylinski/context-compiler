from __future__ import annotations

import os
from anthropic import Anthropic

from .tools.search import semantic_search
from .models import Document


def retrieve_baseline(corpus: dict[str, Document], question: str, top_k: int = 3) -> list[dict]:
    return semantic_search(corpus, question, limit=top_k)


def build_baseline_context(corpus: dict[str, Document], question: str, top_k: int = 3) -> tuple[str, list[dict]]:
    """Build the control context exactly like a common chunk-RAG path.

    The baseline gets the same underlying corpus text but not the structured temporal,
    version, authority, or reference relations used by Context Compiler. That distinction
    is the point of the experiment: similarity-selected text vs compiled evidence.
    """
    hits = retrieve_baseline(corpus, question, top_k)
    blocks = []
    for hit in hits:
        doc = corpus[hit["id"]]
        blocks.append(f"# {doc.title} ({doc.id})\n{doc.body}")
    return "\n\n---\n\n".join(blocks), hits


def _usage(response) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    return {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
    }


def answer_baseline(corpus: dict[str, Document], question: str, query_date=None, top_k: int = 3) -> dict:
    """Naive one-shot RAG control: retrieve top-k text once, answer once."""
    context, hits = build_baseline_context(corpus, question, top_k)
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    date_text = query_date.isoformat() if query_date else "not supplied"

    response = client.messages.create(
        model=model,
        max_tokens=600,
        system=(
            "Answer using only the retrieved chunks below. Be concise and cite document ids. "
            "You do not have access to any hidden metadata or additional retrieval. "
            "If the retrieved chunks appear sufficient, answer directly; otherwise say UNKNOWN."
        ),
        messages=[
            {
                "role": "user",
                "content": f"Query date: {date_text}\nQuestion: {question}\n\nRetrieved chunks:\n{context}",
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
        "mode": "one-shot-top-k-chunks",
        "usage": _usage(response),
        "limitations": ["no version graph", "no temporal validity tool", "no authority graph", "no second retrieval pass"],
    }
