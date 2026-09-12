from __future__ import annotations

import asyncio
import json
import os
import queue
import threading
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .tools import load_corpus
from .baseline import answer_baseline, retrieve_baseline
from .agent import run_compiler
from .challenge import CHALLENGES, make_challenge_candidate, reason_codes
from .certificate import create_certificate, verify_certificate
from .stream_events import set_event_sink, reset_event_sink

ROOT = Path(__file__).resolve().parents[1]
CORPUS = load_corpus(ROOT / "corpus")

app = FastAPI(title="Context Compiler", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str
    query_date: date | None = None


class ChallengeRequest(AskRequest):
    challenge_type: str


class CertificateCreateRequest(BaseModel):
    query_date: date | None = None
    answer: str
    claims: list[dict[str, Any]]


class CertificateVerifyRequest(BaseModel):
    certificate: dict[str, Any]


@app.get("/health")
def health():
    return {
        "ok": True,
        "documents": len(CORPUS),
        "anthropic_key": bool(os.getenv("ANTHROPIC_API_KEY")),
        "model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5"),
    }


@app.post("/baseline")
def baseline(req: AskRequest):
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY is not configured")
    try:
        return answer_baseline(CORPUS, req.question, req.query_date, top_k=3)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Baseline failed: {exc}") from exc


@app.post("/baseline-stream")
def baseline_stream(req: AskRequest):
    """Stream the real one-shot RAG phases: retrieve once, then answer once."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY is not configured")

    async def stream():
        events: queue.Queue[dict] = queue.Queue()

        def worker() -> None:
            try:
                result = answer_baseline(
                    CORPUS,
                    req.question,
                    req.query_date,
                    top_k=3,
                    event_sink=lambda event: events.put({"kind": "event", "event": event}),
                )
                events.put({"kind": "result", "result": result})
            except Exception as exc:
                events.put({"kind": "error", "error": str(exc)})
            finally:
                events.put({"kind": "done"})

        threading.Thread(target=worker, daemon=True).start()
        while True:
            item = await asyncio.to_thread(events.get)
            yield json.dumps(item, ensure_ascii=False) + "\n"
            if item.get("kind") == "done":
                break

    return StreamingResponse(stream(), media_type="application/x-ndjson")


@app.post("/compiler")
def compiler(req: AskRequest):
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY is not configured")
    try:
        return run_compiler(CORPUS, req.question, req.query_date)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Compiler failed: {exc}") from exc


@app.post("/compiler-stream")
def compiler_stream(req: AskRequest):
    """Stream real agent events as NDJSON while the compiler is still running."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY is not configured")

    async def stream():
        events: queue.Queue[dict] = queue.Queue()

        def worker() -> None:
            token = set_event_sink(lambda event: events.put({"kind": "event", "event": asdict(event)}))
            try:
                result = run_compiler(CORPUS, req.question, req.query_date)
                events.put({"kind": "result", "result": result})
            except Exception as exc:
                events.put({"kind": "error", "error": str(exc)})
            finally:
                reset_event_sink(token)
                events.put({"kind": "done"})

        threading.Thread(target=worker, daemon=True).start()

        while True:
            item = await asyncio.to_thread(events.get)
            yield json.dumps(item, ensure_ascii=False) + "\n"
            if item.get("kind") == "done":
                break

    return StreamingResponse(stream(), media_type="application/x-ndjson")


@app.post("/certificate/create")
def certificate_create(req: CertificateCreateRequest):
    bundle = {"status": "SUPPORTED", "answer": req.answer, "claims": req.claims, "unresolved": []}
    certificate = create_certificate(bundle, CORPUS, req.query_date)
    if certificate is None:
        raise HTTPException(status_code=400, detail="answer is not eligible for a release receipt")
    return {"certificate": certificate}


@app.post("/certificate/verify")
def certificate_verify(req: CertificateVerifyRequest):
    try:
        return verify_certificate(req.certificate, CORPUS)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"certificate verification failed: {exc}") from exc


@app.get("/challenge-types")
def challenge_types():
    return [{"type": key, **value} for key, value in CHALLENGES.items()]


@app.post("/challenge")
def challenge(req: ChallengeRequest):
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY is not configured")
    try:
        injected = make_challenge_candidate(CORPUS, req.question, req.query_date, req.challenge_type)
        if not injected["blocked"]:
            raise RuntimeError("challenge mutation unexpectedly passed verification")
        challenge_date = date.fromisoformat(injected["challenge_date"])
        repaired = run_compiler(CORPUS, req.question, challenge_date)
        return {"challenge": {**injected, "reason_codes": reason_codes(injected["verification"])}, "repaired": repaired}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Challenge failed: {exc}") from exc


@app.get("/diagnostics/retrieval")
def retrieval_diagnostics(
    question: str = "Can a contractor access customer data from a personal laptop using VPN?",
    top_k: int = 8,
):
    top_k = max(1, min(top_k, 20))
    hits = retrieve_baseline(CORPUS, question, top_k=top_k)
    ids = [hit["id"] for hit in hits]
    return {
        "question": question,
        "hits": hits,
        "temporal_trap": {
            "historical_policy": "security-policy-2024",
            "historical_rank": ids.index("security-policy-2024") + 1 if "security-policy-2024" in ids else None,
            "current_policy": "security-policy-2025",
            "current_rank": ids.index("security-policy-2025") + 1 if "security-policy-2025" in ids else None,
            "historical_missing_from_top3": "security-policy-2024" not in ids[:3],
            "current_present_in_top3": "security-policy-2025" in ids[:3],
        },
        "note": "This endpoint performs retrieval only; it makes no Anthropic API call.",
    }


@app.get("/demo-cases")
def demo_cases():
    return [
        {
            "label": "Ship Order #4821",
            "mode": "shipping",
            "question": "Can Order #4821 ship today as one parcel via PolarExpress Air Next-Day to Tromsø? If not, determine a compliant alternative shipping plan from the approved corpus.",
            "query_date": "2026-09-12",
            "expected": "Do not ship as one parcel; split the perfume and power bank into approved services and packaging.",
            "action": "Ship Order #4821",
            "order": {
                "destination": "Tromsø, Norway",
                "requested_service": "PolarExpress Air Next-Day",
                "items": ["Fjord Mist perfume · 100 ml", "PB20 power bank · 20,000 mAh"],
                "requested_plan": "One parcel · ship today",
            },
        },
        {"label": "Before policy change", "question": "Can a contractor access customer data from a personal laptop using VPN?", "query_date": "2025-06-10", "expected": "YES, but only with VPN and full-disk encryption"},
        {"label": "After policy change", "question": "Can a contractor access customer data from a personal laptop using VPN?", "query_date": "2025-08-10", "expected": "NO, company-managed device required"},
        {"label": "Multi-hop AI policy", "question": "Can an employee paste customer data into an external AI assistant?", "query_date": "2025-08-10", "expected": "NO unless that AI provider is explicitly approved for Confidential data"},
        {"label": "Knowledge boundary", "question": "Can a contractor expense their spouse's breakfast?", "query_date": "2025-08-10", "expected": "UNKNOWN"},
    ]
