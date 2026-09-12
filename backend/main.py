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
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .tools import load_corpus
from .baseline import answer_baseline, retrieve_baseline
from .agent import run_compiler
from .gate import BasicAuthMiddleware
from .challenge import CHALLENGES, make_challenge_candidate, reason_codes
from .certificate import create_certificate, verify_certificate
from .stream_events import set_event_sink, reset_event_sink

ROOT = Path(__file__).resolve().parents[1]
CORPUS = load_corpus(ROOT / "corpus")

app = FastAPI(title="Context Compiler", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://hackathon.bartoszkobylinski.com", "http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Added last, so it wraps everything else — including the StaticFiles mount.
# No-op unless DEMO_AUTH_USER and DEMO_AUTH_PASSWORD are both set.
app.add_middleware(BasicAuthMiddleware)


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
    question: str = "Can Order #4821 ship today as one parcel via PolarExpress Air Next-Day to Tromsø?",
    top_k: int = 8,
):
    top_k = max(1, min(top_k, 20))
    hits = retrieve_baseline(CORPUS, question, top_k=top_k)
    return {
        "question": question,
        "hits": hits,
        "note": "Retrieval-only diagnostics. Operational correctness may require dependencies outside top-k.",
    }


@app.get("/demo-cases")
def demo_cases():
    return [
        {
            "label": "Mixed restricted goods",
            "mode": "shipping",
            "question": "Can Order #4821 ship today as one parcel via PolarExpress Air Next-Day to Tromsø? If not, determine a compliant alternative shipping plan from the approved corpus.",
            "query_date": "2026-09-12",
            "expected": "Split perfume and power bank because their restricted-goods and packaging rules conflict.",
        },
        {
            "label": "Cold chain + weather",
            "mode": "shipping",
            "question": "Can Order #5902 ship today to Tromsø on PolarExpress Air Next-Day using the available packaging while preserving its 2–8°C requirement and the customer's next-business-day request? If the requested plan cannot be released, determine the safest approved alternative.",
            "query_date": "2026-09-12",
            "expected": "Resolve temperature-control requirements, packaging inventory, weather disruption and service alternatives instead of assuming express means safe.",
        },
        {
            "label": "Live animal + weekend",
            "mode": "shipping",
            "question": "Can Order #6107, containing a live ornamental gecko, be dispatched today to Tromsø on the requested service? If not, determine when and how it can next be shipped from the approved corpus.",
            "query_date": "2026-09-12",
            "expected": "Requested express service is not live-animal approved; weekend and weather acceptance constraints must also be satisfied.",
        },
        {
            "label": "Glass + cheapest service",
            "mode": "shipping",
            "question": "Can Order #7710 ship today to Bergen using the customer's cheapest Standard Economy choice with no signature? If not, determine a compliant service and packaging plan.",
            "query_date": "2026-09-12",
            "expected": "Fragile packaging, declared value, insurance and signature requirements override the customer's cheapest-service preference.",
        },
        {
            "label": "High value + remote address",
            "mode": "shipping",
            "question": "Can Order #8820 meet the customer's requested leave-at-door delivery before 10:00 on 13 September 2026 at the Senja address? If not, determine the earliest compliant delivery plan supported by the corpus.",
            "query_date": "2026-09-12",
            "expected": "High-value signature and supervisor rules conflict with leave-at-door, and the remote address has no staffed Sunday delivery.",
        },
    ]


FRONTEND = ROOT / "frontend"


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    """Serve the UI with its API base pointed at whatever origin served it.

    frontend/app.js falls back to http://localhost:4865, which is wrong as soon as
    the page is served from a domain, and an empty string is falsy there — so the
    origin is injected instead of defaulted.
    """
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(
        html.replace(
            "<head>",
            "<head><script>window.CONTEXT_COMPILER_API=location.origin;</script>",
            1,
        )
    )


# Catch-all: must stay below every API route.
app.mount("/", StaticFiles(directory=FRONTEND), name="frontend")
