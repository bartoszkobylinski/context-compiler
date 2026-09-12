from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .tools import load_corpus
from .baseline import answer_baseline, retrieve_baseline
from .agent import run_compiler

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


@app.get("/health")
def health():
    return {
        "ok": True,
        "documents": len(CORPUS),
        "anthropic_key": bool(os.getenv("ANTHROPIC_API_KEY")),
        "model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5"),
    }


@app.post("/baseline")
def baseline(req: AskRequest):
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY is not configured")
    try:
        return answer_baseline(CORPUS, req.question, req.query_date, top_k=3)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Baseline failed: {exc}") from exc


@app.post("/compiler")
def compiler(req: AskRequest):
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY is not configured")
    try:
        return run_compiler(CORPUS, req.question, req.query_date)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Compiler failed: {exc}") from exc


@app.get("/diagnostics/retrieval")
def retrieval_diagnostics(
    question: str = "Can a contractor access customer data from a personal laptop using VPN?",
    top_k: int = 8,
):
    """Offline retrieval inspection: no model call and no API spend."""
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
            "label": "Before policy change",
            "question": "Can a contractor access customer data from a personal laptop using VPN?",
            "query_date": "2025-06-10",
            "expected": "YES, but only with VPN and full-disk encryption",
        },
        {
            "label": "After policy change",
            "question": "Can a contractor access customer data from a personal laptop using VPN?",
            "query_date": "2025-08-10",
            "expected": "NO, company-managed device required",
        },
        {
            "label": "Multi-hop AI policy",
            "question": "Can an employee paste customer data into an external AI assistant?",
            "query_date": "2025-08-10",
            "expected": "NO unless that AI provider is explicitly approved for Confidential data",
        },
        {
            "label": "Knowledge boundary",
            "question": "Can a contractor expense their spouse's breakfast?",
            "query_date": "2025-08-10",
            "expected": "UNKNOWN",
        },
    ]
