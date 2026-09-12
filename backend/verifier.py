from __future__ import annotations

import re
from datetime import date
from typing import Any

from .models import Document
from .temporal import valid_at


_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "because", "but", "by", "can",
    "do", "does", "for", "from", "has", "have", "if", "in", "is", "it", "may",
    "must", "no", "not", "of", "on", "only", "or", "so", "that", "the", "their",
    "this", "to", "use", "uses", "using", "was", "were", "when", "with", "yes",
}


def _terms(text: str) -> set[str]:
    """Normalize content words for a conservative deterministic coverage check."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    normalized: set[str] = set()
    for token in tokens:
        if token in _STOPWORDS or len(token) <= 2:
            continue
        # Tiny stemmer: enough to align requires/required and connections/connection
        # without introducing an NLP dependency into the verifier.
        for suffix in ("ing", "ed", "es", "s"):
            if token.endswith(suffix) and len(token) - len(suffix) >= 4:
                token = token[: -len(suffix)]
                break
        normalized.add(token)
    return normalized


def _material_sentences(text: str) -> list[str]:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]
    # Very short answer fragments such as "No." are conclusions rather than standalone
    # factual assertions and are allowed to ride on the claims that follow.
    return [sentence for sentence in sentences if len(_terms(sentence)) >= 3]


def _answer_coverage(answer_text: str, claims: list[dict[str, Any]]) -> dict[str, Any]:
    """Require every material answer sentence to be traceable to a declared claim.

    This closes the gap where a model can provide verified claims but smuggle an extra,
    unsupported factual sentence into the user-facing prose. Coverage is intentionally
    deterministic and lexical; it does not pretend to prove semantic equivalence.
    """
    claim_terms = [_terms(str(claim.get("claim", ""))) for claim in claims]
    checks: list[dict[str, Any]] = []
    uncovered: list[str] = []

    for sentence in _material_sentences(answer_text):
        terms = _terms(sentence)
        best_index = None
        best_score = 0.0
        for index, candidate in enumerate(claim_terms):
            if not candidate:
                continue
            overlap = len(terms & candidate)
            score = overlap / max(1, min(len(terms), len(candidate)))
            if score > best_score:
                best_score = score
                best_index = index

        covered = best_score >= 0.45
        checks.append(
            {
                "sentence": sentence,
                "covered": covered,
                "claim_index": None if best_index is None else best_index + 1,
                "score": round(best_score, 3),
            }
        )
        if not covered:
            uncovered.append(sentence)

    return {"complete": not uncovered, "checks": checks, "uncovered": uncovered}


def verify_answer(
    answer: dict[str, Any],
    corpus: dict[str, Document],
    query_date: date | None,
) -> dict[str, Any]:
    """Deterministically verify the evidence contract of a final answer.

    A SUPPORTED answer is accepted only when every material claim:
    - cites an existing approved document,
    - includes a short verbatim supporting quote,
    - when a query date is supplied, cites a source valid at that date,
    - and every material sentence in the user-facing answer is covered by one of the
      declared claims.

    This is intentionally stricter than asking the model whether it is grounded.
    """
    status = answer.get("status")
    claims = answer.get("claims", [])

    if status == "UNKNOWN":
        unresolved = answer.get("unresolved", [])
        return {
            "complete": bool(unresolved),
            "missing": [] if unresolved else ["UNKNOWN requires an explicit evidence gap"],
            "checks": [],
            "coverage": {"complete": True, "checks": [], "uncovered": []},
        }

    if status == "CONFLICT":
        unresolved = answer.get("unresolved", [])
        return {
            "complete": bool(unresolved),
            "missing": [] if unresolved else ["CONFLICT requires an explicit unresolved conflict"],
            "checks": [],
            "coverage": {"complete": True, "checks": [], "uncovered": []},
        }

    if status != "SUPPORTED":
        return {
            "complete": False,
            "missing": [f"unsupported final status: {status!r}"],
            "checks": [],
            "coverage": {"complete": False, "checks": [], "uncovered": []},
        }

    if not claims:
        return {
            "complete": False,
            "missing": ["no material claims supplied"],
            "checks": [],
            "coverage": {"complete": False, "checks": [], "uncovered": []},
        }

    missing: list[str] = []
    checks: list[dict[str, Any]] = []

    for idx, claim in enumerate(claims, start=1):
        claim_text = str(claim.get("claim", "")).strip()
        source_id = str(claim.get("source_id", "")).strip()
        quote = str(claim.get("quote", "")).strip()
        errors: list[str] = []

        if not claim_text:
            errors.append("claim text missing")

        doc = corpus.get(source_id) if source_id else None
        if doc is None:
            errors.append(f"unknown source_id {source_id!r}")
        else:
            if not quote:
                errors.append("supporting quote missing")
            elif quote not in doc.body:
                errors.append("supporting quote is not verbatim in cited source")

            if query_date is not None and not valid_at(doc, query_date):
                errors.append(f"source is not valid at {query_date.isoformat()}")

        checks.append(
            {
                "claim": claim_text,
                "source_id": source_id,
                "quote": quote,
                "valid_at_query_time": None if doc is None or query_date is None else valid_at(doc, query_date),
                "ok": not errors,
                "errors": errors,
            }
        )
        if errors:
            missing.append(f"claim {idx}: " + "; ".join(errors))

    coverage = _answer_coverage(str(answer.get("answer", "")), claims)
    for sentence in coverage["uncovered"]:
        missing.append(f"answer contains material text not covered by a declared claim: {sentence}")

    return {
        "complete": not missing,
        "missing": missing,
        "checks": checks,
        "coverage": coverage,
    }
