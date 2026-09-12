from __future__ import annotations

from datetime import date
from typing import Any

from .models import Document
from .temporal import valid_at


def verify_answer(
    answer: dict[str, Any],
    corpus: dict[str, Document],
    query_date: date | None,
) -> dict[str, Any]:
    """Deterministically verify the evidence contract of a final answer.

    A SUPPORTED answer is accepted only when every material claim:
    - cites an existing approved document,
    - includes a short verbatim supporting quote,
    - and, when a query date is supplied, cites a source valid at that date.

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
        }

    if status == "CONFLICT":
        unresolved = answer.get("unresolved", [])
        return {
            "complete": bool(unresolved),
            "missing": [] if unresolved else ["CONFLICT requires an explicit unresolved conflict"],
            "checks": [],
        }

    if status != "SUPPORTED":
        return {
            "complete": False,
            "missing": [f"unsupported final status: {status!r}"],
            "checks": [],
        }

    if not claims:
        return {"complete": False, "missing": ["no material claims supplied"], "checks": []}

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

    return {"complete": not missing, "missing": missing, "checks": checks}
