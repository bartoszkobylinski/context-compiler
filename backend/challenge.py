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

PRIMARY_DEMO_DATE = date(2025, 6, 10)


def make_challenge_candidate(
    corpus: dict[str, Document],
    question: str,
    query_date: date | None,
    challenge_type: str,
) -> dict[str, Any]:
    """Build a deliberately bad candidate for the primary temporal demo.

    Challenge mode is intentionally reproducible on stage. Each mutation isolates one
    deterministic verifier invariant so the audience sees one clean failure mode at a
    time instead of accidental combinations caused by the currently selected demo date.
    """
    if challenge_type not in CHALLENGES:
        raise ValueError(f"unknown challenge type: {challenge_type}")

    if "personal laptop" not in question.lower() or "customer data" not in question.lower():
        raise ValueError("challenge mode is currently scoped to the personal-device demo question")

    # Adversarial challenge mode is pinned to the before-change point in time. This makes
    # the three attacks deterministic and prevents quote/coverage challenges from also
    # failing merely because the UI happens to be on the after-change preset.
    challenge_date = PRIMARY_DEMO_DATE

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
                    # Deliberately wrong by one phrase: the real source says corporate tunnel.
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

    verification = verify_answer(candidate, corpus, challenge_date)
    return {
        "type": challenge_type,
        **CHALLENGES[challenge_type],
        "candidate": candidate,
        "verification": verification,
        "blocked": not verification["complete"],
        "challenge_date": challenge_date.isoformat(),
        "requested_date": query_date.isoformat() if query_date else None,
    }


def reason_codes(verification: dict[str, Any]) -> list[str]:
    codes: list[str] = []
    for reason in verification.get("missing", []):
        value = reason.lower()
        # A single verifier message can contain more than one invariant failure; surface
        # every matching code instead of masking later errors with an elif chain.
        matches: list[str] = []
        if "not valid at" in value:
            matches.append("TEMPORAL_INVALID")
        if "not verbatim" in value or "quote" in value:
            matches.append("QUOTE_MISMATCH")
        if "not covered by a declared claim" in value:
            matches.append("ANSWER_COVERAGE")
        if "unknown source" in value:
            matches.append("SOURCE_MISSING")
        if not matches:
            matches.append("EVIDENCE_INCOMPLETE")
        for code in matches:
            if code not in codes:
                codes.append(code)
    return codes
