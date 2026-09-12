from __future__ import annotations


def basic_verification(answer: dict) -> dict:
    """Small deterministic gate used by the MVP.

    The agent must return citations for each material claim. Later this can be replaced by
    a second model pass that atomizes claims and validates them against collected evidence.
    """
    claims = answer.get("claims", [])
    if not claims:
        return {"complete": False, "missing": ["no claims supplied"]}

    unsupported = [c for c in claims if not c.get("source_id")]
    return {
        "complete": len(unsupported) == 0,
        "missing": [c.get("claim", "unnamed claim") for c in unsupported],
    }
