from __future__ import annotations

from datetime import date
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel

from .tools import load_corpus
from .baseline import retrieve_baseline
from .agent import run_demo_compiler

ROOT = Path(__file__).resolve().parents[1]
CORPUS = load_corpus(ROOT / "corpus")

app = FastAPI(title="Context Compiler")


class AskRequest(BaseModel):
    question: str
    query_date: date | None = None


@app.get("/health")
def health():
    return {"ok": True, "documents": len(CORPUS)}


@app.post("/baseline")
def baseline(req: AskRequest):
    return {
        "question": req.question,
        "hits": retrieve_baseline(CORPUS, req.question, top_k=3),
        "note": "Wire Anthropic answer generation here during the hackathon.",
    }


@app.post("/compiler")
def compiler(req: AskRequest):
    return run_demo_compiler(CORPUS, req.question, req.query_date)
