from __future__ import annotations

from datetime import date
from .models import AgentState, ToolEvent, Evidence, Document
from .temporal import explain_validity
from .tools import semantic_search, get_versions


def run_demo_compiler(corpus: dict[str, Document], question: str, query_date: date | None) -> dict:
    """Deterministic scaffold for the demo flow.

    This intentionally makes the state/event model real before wiring Claude tool use.
    Replace the routing logic with Anthropic tool calls during the hackathon while keeping
    the same event contract for the frontend.
    """
    state = AgentState(question=question, query_date=query_date)

    state.events.append(ToolEvent("SEARCHING", "Searching remote access and device policy"))
    hits = semantic_search(corpus, question, limit=5)
    state.events.append(ToolEvent("DOCUMENT_FOUND", f"Found {len(hits)} candidate documents", {"hits": hits}))

    versions = get_versions(corpus, "Security Policy")
    if len(versions) > 1:
        state.events.append(ToolEvent("VERSION_CONFLICT", "Multiple Security Policy versions detected", {"versions": [v["id"] for v in versions]}))

    applicable = None
    if query_date:
        for version in versions:
            check = explain_validity(corpus[version["id"]], query_date)
            state.events.append(ToolEvent("TEMPORAL_CHECK", f"Checked {version['id']} at {query_date.isoformat()}", check))
            if check["valid"]:
                applicable = corpus[version["id"]]

    if applicable:
        state.events.append(ToolEvent("EVIDENCE_ADDED", f"Using {applicable.id} as temporally applicable policy"))
        if applicable.id == "security-policy-2024":
            state.evidence.extend([
                Evidence("Personal devices are allowed for customer data only with VPN and full-disk encryption.", applicable.id, "4.2", True, applicable.authority),
                Evidence("Contractors may remotely access systems subject to security controls.", "contractor-handbook", "3", True, "official"),
            ])
            answer = "YES — on this date, a contractor may use a personal laptop only if VPN and full-disk encryption requirements are satisfied."
        else:
            state.evidence.extend([
                Evidence("Customer data may only be accessed from company-managed devices.", applicable.id, "4.2", True, applicable.authority),
                Evidence("VPN remains mandatory for remote access but is not sufficient by itself.", "vpn-policy", "2.1", True, "official"),
            ])
            answer = "NO — on this date, customer data may only be accessed from a company-managed device. VPN alone is insufficient."

        state.events.append(ToolEvent("VERIFYING", f"Verifying {len(state.evidence)} material claims"))
        state.events.append(ToolEvent("SUPPORTED", f"{len(state.evidence)}/{len(state.evidence)} claims supported"))
        return {
            "status": "SUPPORTED",
            "answer": answer,
            "events": [e.__dict__ for e in state.events],
            "evidence": [e.__dict__ for e in state.evidence],
        }

    state.events.append(ToolEvent("EVIDENCE_GAP", "No temporally applicable source resolves the question"))
    return {
        "status": "UNKNOWN",
        "answer": "UNKNOWN — insufficient approved evidence.",
        "events": [e.__dict__ for e in state.events],
        "evidence": [],
    }
