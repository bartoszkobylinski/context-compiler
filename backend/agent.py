from __future__ import annotations

import json
import os
from datetime import date
from typing import Any

from anthropic import Anthropic

from .models import AgentState, ToolEvent, Document
from .temporal import explain_validity
from .tools import (
    semantic_search,
    keyword_search,
    open_document,
    get_versions,
    follow_reference,
)
from .verifier import verify_answer


SYSTEM_PROMPT = """You are Context Compiler, an evidence-building agent.

Your job is NOT to answer immediately. First declare what evidence must be established,
then use tools iteratively to gather it.

Rules:
1. Your FIRST tool call must be declare_requirements. List the concrete facts that must
   be established before the question can be answered safely.
2. Treat retrieval as a loop, not a one-shot lookup.
3. Prefer authoritative and temporally valid sources.
4. If multiple versions of a policy exist, explicitly inspect the versions and check
   which one was valid at the user's query date.
5. If a source references another source needed to answer, follow the reference.
6. Never infer a policy merely because it sounds likely.
7. If the approved corpus does not establish the answer, return UNKNOWN.
8. Before answering, ensure every material factual claim is backed by a source.
9. For every supported claim include a SHORT VERBATIM quote copied exactly from the
   cited document. The deterministic verifier checks exact quote membership.
10. Every material factual sentence in the user-facing answer must be represented by
    one of the claims. Do not add background, predictions, typical behavior, or other
    prose that is not explicitly covered by a cited claim.

When you are ready to stop using tools, respond ONLY with JSON in this exact shape:
{
  "status": "SUPPORTED" | "UNKNOWN" | "CONFLICT",
  "answer": "concise user-facing answer",
  "claims": [
    {
      "claim": "material factual claim",
      "source_id": "document-id",
      "section": "optional section",
      "quote": "short exact quote copied verbatim from the document"
    }
  ],
  "unresolved": ["anything still not established"]
}

If status is UNKNOWN, claims may be empty and unresolved must explain what evidence is missing.
"""


TOOLS = [
    {
        "name": "declare_requirements",
        "description": "Declare the concrete evidence requirements that must be satisfied before answering. This must be your first tool call.",
        "input_schema": {
            "type": "object",
            "properties": {
                "requirements": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 8,
                }
            },
            "required": ["requirements"],
        },
    },
    {
        "name": "semantic_search",
        "description": "Find documents semantically/lexically related to a query. Use for broad discovery.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 8},
            },
            "required": ["query"],
        },
    },
    {
        "name": "keyword_search",
        "description": "Find documents using exact words/phrases. Useful after semantic search or for policy terms.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 8},
            },
            "required": ["query"],
        },
    },
    {
        "name": "open_document",
        "description": "Open one document and inspect its body plus metadata.",
        "input_schema": {
            "type": "object",
            "properties": {"document_id": {"type": "string"}},
            "required": ["document_id"],
        },
    },
    {
        "name": "get_versions",
        "description": "List all known versions of a document title, including validity metadata.",
        "input_schema": {
            "type": "object",
            "properties": {"title": {"type": "string"}},
            "required": ["title"],
        },
    },
    {
        "name": "valid_at",
        "description": "Deterministically check whether one document was valid at a given date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "document_id": {"type": "string"},
                "date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
            },
            "required": ["document_id", "date"],
        },
    },
    {
        "name": "follow_reference",
        "description": "Open a document explicitly referenced by another document.",
        "input_schema": {
            "type": "object",
            "properties": {
                "document_id": {"type": "string"},
                "reference_id": {"type": "string"},
            },
            "required": ["document_id", "reference_id"],
        },
    },
]


def _client() -> Anthropic:
    return Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def _model() -> str:
    return os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")


def _event_type(tool_name: str, result: Any) -> str:
    if tool_name == "declare_requirements":
        return "EVIDENCE_REQUIREMENTS"
    if tool_name in {"semantic_search", "keyword_search"}:
        return "SEARCHING"
    if tool_name == "get_versions":
        return "VERSION_CHECK"
    if tool_name == "valid_at":
        return "TEMPORAL_CHECK"
    if tool_name == "follow_reference":
        return "FOLLOWING_REFERENCE"
    if tool_name == "open_document":
        return "DOCUMENT_FOUND"
    return "TOOL"


def _event_message(tool_name: str, args: dict[str, Any], result: Any) -> str:
    if tool_name == "declare_requirements":
        reqs = args.get("requirements", [])
        return "Need to establish: " + " • ".join(reqs)
    if tool_name in {"semantic_search", "keyword_search"}:
        return f"Search: {args.get('query', '')}"
    if tool_name == "open_document":
        title = result.get("title") if isinstance(result, dict) else None
        return f"Opened {title or args.get('document_id')}"
    if tool_name == "get_versions":
        ids = [item.get("id") for item in result] if isinstance(result, list) else []
        return "Versions found: " + " → ".join(filter(None, ids))
    if tool_name == "valid_at":
        valid = bool(result.get("valid")) if isinstance(result, dict) else False
        marker = "VALID" if valid else "NOT VALID"
        reason = result.get("reason", "") if isinstance(result, dict) else ""
        return f"{args.get('document_id')} @ {args.get('date')}: {marker}" + (f" · {reason}" if reason else "")
    if tool_name == "follow_reference":
        return f"Following reference: {args.get('document_id')} → {args.get('reference_id')}"
    return tool_name


def _execute_tool(corpus: dict[str, Document], name: str, args: dict[str, Any]) -> Any:
    if name == "declare_requirements":
        return {"requirements": args["requirements"], "accepted": True}
    if name == "semantic_search":
        return semantic_search(corpus, args["query"], limit=args.get("limit", 5))
    if name == "keyword_search":
        return keyword_search(corpus, args["query"], limit=args.get("limit", 5))
    if name == "open_document":
        return open_document(corpus, args["document_id"])
    if name == "get_versions":
        return get_versions(corpus, args["title"])
    if name == "valid_at":
        when = date.fromisoformat(args["date"])
        return explain_validity(corpus[args["document_id"]], when)
    if name == "follow_reference":
        return follow_reference(corpus, args["document_id"], args["reference_id"])
    raise ValueError(f"Unknown tool: {name}")


def _json_from_text(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # The model sometimes narrates before the object ("Now I'll finalize...").
    # Take the first complete JSON object embedded in the text instead.
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text, index)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("no JSON object found in model output")


def run_compiler(corpus: dict[str, Document], question: str, query_date: date | None) -> dict[str, Any]:
    """Run the Anthropic evidence-building loop with a deterministic final verifier."""
    state = AgentState(question=question, query_date=query_date)
    client = _client()
    requirements_declared = False
    usage = {"input_tokens": 0, "output_tokens": 0}

    date_text = query_date.isoformat() if query_date else "not explicitly supplied"
    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": (
                f"Question: {question}\n"
                f"Query date: {date_text}\n\n"
                "Build sufficient evidence before answering. If the corpus cannot establish the answer, return UNKNOWN."
            ),
        }
    ]

    for step in range(state.max_steps):
        state.step = step + 1
        response = client.messages.create(
            model=_model(),
            max_tokens=8000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        response_usage = getattr(response, "usage", None)
        if response_usage is not None:
            usage["input_tokens"] += int(getattr(response_usage, "input_tokens", 0) or 0)
            usage["output_tokens"] += int(getattr(response_usage, "output_tokens", 0) or 0)

        tool_uses = [block for block in response.content if getattr(block, "type", None) == "tool_use"]
        text_blocks = [block.text for block in response.content if getattr(block, "type", None) == "text"]

        if tool_uses:
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for tool_use in tool_uses:
                if not requirements_declared and tool_use.name != "declare_requirements":
                    error = "declare_requirements must be the first tool call"
                    state.events.append(ToolEvent("TOOL_ERROR", error))
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "is_error": True,
                            "content": error,
                        }
                    )
                    continue
                if requirements_declared and tool_use.name == "declare_requirements":
                    error = "evidence requirements have already been declared"
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "is_error": True,
                            "content": error,
                        }
                    )
                    continue

                try:
                    result = _execute_tool(corpus, tool_use.name, tool_use.input)
                    if tool_use.name == "declare_requirements":
                        requirements_declared = True
                        state.unresolved = list(tool_use.input.get("requirements", []))

                    event_type = _event_type(tool_use.name, result)
                    state.events.append(
                        ToolEvent(
                            event_type,
                            _event_message(tool_use.name, tool_use.input, result),
                            {"tool": tool_use.name, "input": tool_use.input, "result": result},
                        )
                    )
                    if tool_use.name == "valid_at" and isinstance(result, dict) and not result.get("valid"):
                        state.events.append(
                            ToolEvent(
                                "OUTDATED_SOURCE",
                                f"Rejected {tool_use.input.get('document_id')} for this point in time",
                                {"reason": result.get("reason")},
                            )
                        )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )
                except Exception as exc:
                    state.events.append(ToolEvent("TOOL_ERROR", f"{tool_use.name} failed", {"error": str(exc)}))
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "is_error": True,
                            "content": str(exc),
                        }
                    )
            messages.append({"role": "user", "content": tool_results})
            continue

        if not requirements_declared:
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": "You must call declare_requirements before answering or searching."})
            continue

        if not text_blocks:
            state.events.append(ToolEvent("EVIDENCE_GAP", "Model stopped without an answer"))
            break

        final_text = "\n".join(text_blocks)
        try:
            answer = _json_from_text(final_text)
        except Exception:
            state.events.append(ToolEvent("FORMAT_ERROR", "Model returned non-JSON final output", {"raw": final_text}))
            messages.append({"role": "assistant", "content": final_text})
            messages.append({"role": "user", "content": "Return only the required JSON object. Continue gathering evidence if needed."})
            continue

        verification = verify_answer(answer, corpus, query_date)
        state.events.append(
            ToolEvent(
                "VERIFYING",
                f"Deterministically verifying {len(answer.get('claims', []))} material claims and answer coverage",
                {
                    "checks": verification["checks"],
                    "coverage": verification.get("coverage", {}),
                },
            )
        )

        if not verification["complete"]:
            state.events.append(
                ToolEvent(
                    "EVIDENCE_GAP",
                    "Verifier rejected the proposed final answer",
                    {"missing": verification["missing"]},
                )
            )
            messages.append({"role": "assistant", "content": final_text})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "The deterministic verifier rejected this answer for these reasons:\n- "
                        + "\n- ".join(verification["missing"])
                        + "\nEvery material sentence in the answer must map to a declared claim. "
                        "Use tools again to repair the evidence, remove unsupported prose, or return UNKNOWN if it cannot be repaired."
                    ),
                }
            )
            continue

        status = answer.get("status")
        if status == "SUPPORTED":
            state.events.append(
                ToolEvent(
                    "SUPPORTED",
                    f"{len(answer.get('claims', []))}/{len(answer.get('claims', []))} material claims passed deterministic verification",
                    {
                        "checks": verification["checks"],
                        "coverage": verification.get("coverage", {}),
                    },
                )
            )
        elif status == "UNKNOWN":
            state.events.append(ToolEvent("UNKNOWN", "Approved corpus does not establish the answer"))
        else:
            state.events.append(ToolEvent("CONFLICT", "Approved sources remain in unresolved conflict"))

        return {
            **answer,
            "events": [e.__dict__ for e in state.events],
            "verification": verification,
            "requirements": state.unresolved,
            "steps": state.step,
            "model": _model(),
            "usage": usage,
        }

    state.events.append(ToolEvent("UNKNOWN", "Maximum evidence-gathering steps reached"))
    return {
        "status": "UNKNOWN",
        "answer": "UNKNOWN — insufficient verified evidence within the search budget.",
        "events": [e.__dict__ for e in state.events],
        "claims": [],
        "unresolved": ["max evidence-gathering steps reached"],
        "verification": {"complete": True, "missing": [], "checks": [], "coverage": {"complete": True, "checks": [], "uncovered": []}},
        "requirements": state.unresolved,
        "steps": state.step,
        "model": _model(),
        "usage": usage,
    }
