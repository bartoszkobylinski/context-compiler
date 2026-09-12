from __future__ import annotations

import os
from typing import Callable
from anthropic import Anthropic

from .tools.search import semantic_search
from .models import Document


BaselineEventSink = Callable[[dict], None] | None


def retrieve_baseline(corpus: dict[str, Document], question: str, top_k: int = 3) -> list[dict]:
    return semantic_search(corpus, question, limit=top_k)


def _context_from_hits(corpus: dict[str, Document], hits: list[dict]) -> str:
    blocks = []
    for hit in hits:
        doc = corpus[hit["id"]]
        blocks.append(f"# {doc.title} ({doc.id})\n{doc.body}")
    return "\n\n---\n\n".join(blocks)


def _usage(response) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    return {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
    }


def _add_usage(total: dict[str, int], response) -> None:
    current = _usage(response)
    total["input_tokens"] += current["input_tokens"]
    total["output_tokens"] += current["output_tokens"]


def _text(response) -> str:
    return "\n".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()


def _emit(sink: BaselineEventSink, event_type: str, message: str, payload: dict | None = None) -> None:
    if sink is not None:
        sink({"type": event_type, "message": message, "payload": payload or {}})


def answer_baseline(
    corpus: dict[str, Document],
    question: str,
    query_date=None,
    top_k: int = 3,
    event_sink: BaselineEventSink = None,
) -> dict:
    """Stronger two-pass RAG control without evidence contracts or deterministic release gates.

    Pass 1 retrieves top-k chunks. The model sees them and produces one follow-up search query
    for the most important missing evidence. Pass 2 retrieves again, then the model answers from
    the union. This deliberately gives the control another chance to find the right document;
    the comparison is therefore about evidence sufficiency and release gating, not merely the
    number of retrieval calls.
    """
    _emit(event_sink, "QUESTION", "Question received")
    _emit(event_sink, "RETRIEVING", f"Pass 1: searching top-{top_k} similar chunks", {"top_k": top_k, "pass": 1})
    pass1_hits = retrieve_baseline(corpus, question, top_k)
    pass1_context = _context_from_hits(corpus, pass1_hits)
    _emit(event_sink, "TOP_K_READY", f"Pass 1 selected {len(pass1_hits)} chunks", {"hits": pass1_hits, "pass": 1})

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
    date_text = query_date.isoformat() if query_date else "not supplied"
    usage = {"input_tokens": 0, "output_tokens": 0}

    _emit(event_sink, "GAP_QUERY", "Model identifies the single most important missing evidence for one follow-up retrieval", {"model": model})
    gap_response = client.messages.create(
        model=model,
        max_tokens=160,
        system=(
            "You are the query-planning step of a two-pass RAG baseline. You get the user's question and the first retrieved chunks. "
            "Return ONLY one short search query for the most important missing evidence needed to answer the operational question. "
            "Do not answer the question. Do not explain. You get exactly one more retrieval pass."
        ),
        messages=[{
            "role": "user",
            "content": f"Query date: {date_text}\nQuestion: {question}\n\nFirst-pass chunks:\n{pass1_context}",
        }],
    )
    _add_usage(usage, gap_response)
    gap_query = _text(gap_response).strip().strip('"').strip()
    if not gap_query:
        gap_query = f"{question} governing policy eligibility restrictions requirements"

    _emit(event_sink, "RETRIEVING", f"Pass 2: searching for missing evidence: {gap_query}", {"query": gap_query, "top_k": top_k, "pass": 2})
    pass2_hits = semantic_search(corpus, gap_query, limit=top_k)
    _emit(event_sink, "TOP_K_READY", f"Pass 2 selected {len(pass2_hits)} chunks", {"hits": pass2_hits, "pass": 2})

    seen: set[str] = set()
    hits: list[dict] = []
    for hit in [*pass1_hits, *pass2_hits]:
        if hit["id"] in seen:
            continue
        seen.add(hit["id"])
        hits.append(hit)
    context = _context_from_hits(corpus, hits)

    _emit(
        event_sink,
        "ANSWERING",
        "Answering from both retrieval passes — no version graph, evidence contract, deterministic verifier, or repair loop",
        {"model": model, "chunks": len(hits)},
    )
    response = client.messages.create(
        model=model,
        max_tokens=2400,
        system=(
            "Answer the user's operational question as well as you can using only the retrieved chunks below. "
            "Be concise and cite document ids. Make the best supported determination from the supplied chunks and explicitly state important uncertainty. "
            "You have no more retrieval, no structured dependency tools, no evidence requirements contract, and no deterministic release gate."
        ),
        messages=[{
            "role": "user",
            "content": f"Query date: {date_text}\nQuestion: {question}\n\nRetrieved chunks from two passes:\n{context}",
        }],
    )
    _add_usage(usage, response)
    text = _text(response)

    return {
        "answer": text,
        "hits": hits,
        "pass1_hits": pass1_hits,
        "pass2_hits": pass2_hits,
        "followup_query": gap_query,
        "model": model,
        "mode": "two-pass-rag-gap-query",
        "usage": usage,
        "stop_reason": getattr(response, "stop_reason", None),
        "limitations": [
            "one follow-up retrieval only",
            "no reference graph",
            "no deterministic temporal validity gate",
            "no evidence requirement closure",
            "no claim-level release verifier",
            "no repair loop",
        ],
    }
