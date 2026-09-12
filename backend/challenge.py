from __future__ import annotations

from datetime import date
from typing import Any

from .models import Document
from .verifier import verify_answer


CHALLENGES = {
    "future_policy": {
        "label": "Use future policy",
        "description": "Force a real but not-yet-effective policy into the candidate answer.",
    },
    "corrupt_quote": {
        "label": "Corrupt supporting quote",
        "description": "Change one word in an otherwise plausible citation.",
    },
    "unsupported_claim": {
        "label": "Inject unsupported claim",
        "description": "Add a plausible sentence that is not established by the approved corpus.",
    },
}


def make_challenge_candidate(
    corpus: dict[str, Document],
    question: str,
    query_date: date | None,
    challenge_type: str,
) -> dict[str, Any]:
    """Build a deliberately bad candidate for the primary temporal demo.

    The point is adversarial evaluation, not another model call: each mutation targets
    one deterministic verifier invariant so the failure is reproducible on stage.
    """
    if challenge_type not in CHALLENGES:
        raise ValueError(f"unknown challenge type: {challenge_type}")

    if "personal laptop" not in question.lower() or "customer data" not in question.lower():
        raise ValueError("challenge mode is currently scoped to the personal-device demo question")

    if challenge_type == "future_policy":
        candidate = {
            "status": "SUPPORTED",
            "answer": "No. Customer data may only be accessed from company-managed devices.",
            "claims": [
                {
                    "claim": "Customer data may only be accessed from company-managed devices.",
                    "source_id": "security-policy-2025",
                    "section": "4.2 Customer data access",
                    "quote": "Customer data may only be accessed from company-managed devices.",
                }
            ],
            "unresolved": [],
        }
    elif challenge_type == "corrupt_quote":
        candidate = {
            "status": "SUPPORTED",
            "answer": "A personal device may be used only with the corporate tunnel and whole-disk encryption.",
            "claims": [
                {
                    "claim": "A personal device may be used only with the corporate tunnel and whole-disk encryption.",
                    "source_id": "security-policy-2024",
                    "section": "4.2 BYOD access to restricted client records",
                    "quote": "Restricted client records may be viewed on a privately owned computer only when the device uses the corporate VPN and whole-disk encryption.",
                }
            ],
            "unresolved": [],
        }
    else:
        candidate = {
            "status": "SUPPORTED",
            "answer": (
                "A contractor may use a personal laptop with the corporate tunnel and whole-disk encryption. "
                "Most contractors use personal laptops for this kind of access."
            ),
            "claims": [
                {
                    "claim": "Restricted client records may be viewed on a privately owned computer only with the corporate tunnel and whole-disk encryption.",
                    "source_id": "security-policy-2024",
                    "section": "4.2 BYOD access to restricted client records",
                    "quote": "Restricted client records may be viewed on a privately owned computer only when the device uses the corporate tunnel and whole-disk encryption.",
                }
            ],
            "unresolved": [],
        }

    verification = verify_answer(candidate, corpus, query_date)
    return {
        "type": challenge_type,
        **CHALLENGES[challenge_type],
        "candidate": candidate,
        "verification": verification,
        "blocked": not verification["complete"],
    }


def reason_codes(verification: dict[str, Any]) -> list[str]:
    codes: list[str] = []
    for reason in verification.get("missing", []):
        value = reason.lower()
        if "not valid at" in value:
            code = "TEMPORAL_INVALID"
        elif "not verbatim" in value or "quote" in value:
            code = "QUOTE_MISMATCH"
        elif "not covered by a declared claim" in value:
            code = "ANSWER_COVERAGE"
        elif "unknown source" in value:
            code = "SOURCE_MISSING"
        else:
            code = "EVIDENCE_INCOMPLETE"
        if code not in codes:
            codes.append(code)
    return codes
