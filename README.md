# Context Compiler

Hackathon MVP: turn retrieval from a one-shot similarity lookup into an evidence-building loop.

> **We don't make the model know more. We make it prove that it knows enough.**

## Core idea

Traditional RAG:

`question -> top-k chunks -> model -> answer`

Context Compiler:

`question -> evidence requirements -> iterative retrieval -> temporal/authority checks -> deterministic claim verification -> answer or UNKNOWN`

The same corpus is used by both paths. The baseline sees only similarity-selected text chunks. Context Compiler can inspect structured relationships such as versions, validity intervals, authority and explicit references.

## Primary demo

Question:

> Can a contractor access customer data from a personal laptop using VPN?

At **2025-06-10** the expected answer is **YES, conditionally**: Security Policy 2024 is still valid and requires VPN + full-disk encryption.

At **2025-08-10** the expected answer is **NO**: Security Policy 2025 became effective on July 1 and requires a company-managed device.

This demonstrates that every retrieved document can be real and still produce the wrong answer when evidence belongs to the wrong point in time.

## Other demo cases

- **Multi-hop:** Can an employee paste customer data into an external AI assistant? The agent must follow AI Usage Guidelines -> Data Classification Policy -> AI Security Addendum.
- **Knowledge boundary:** Can a contractor expense their spouse's breakfast? The correct answer is **UNKNOWN** because the approved corpus does not establish a rule.
- **Adversarial guidance:** Remote Access Quickstart is highly similar to the security question but is lower-authority guidance and explicitly defers customer-data rules to the Security Policy.

## Evidence contract

A `SUPPORTED` answer is released only when each material claim has:

1. an existing approved `source_id`,
2. a short **verbatim supporting quote** present in that source,
3. a source valid at the requested point in time.

If verification fails, the answer is rejected and the agent goes back into the retrieval loop. If the gap cannot be repaired, the result is `UNKNOWN`.

## Architecture

- `frontend/` — side-by-side Traditional RAG vs Context Compiler demo
- `backend/main.py` — FastAPI endpoints
- `backend/agent.py` — Anthropic tool-use evidence loop
- `backend/verifier.py` — deterministic evidence gate
- `backend/temporal.py` — deterministic validity checks
- `backend/tools/` — search, open, version and reference tools
- `corpus/` — curated Markdown corpus with YAML metadata
- `evals/` — adversarial demo cases + comparison runner
- `tests/` — temporal and verifier tests

## Run locally

```bash
uv sync

cp .env.example .env
# then put your key in .env: ANTHROPIC_API_KEY=...

make api
```

`.env` is loaded automatically on import (`backend/__init__.py`); it overrides any
`ANTHROPIC_*` already exported in the shell.

In another terminal:

```bash
cd frontend
python3 -m http.server 3000
```

Open `http://localhost:3000`.

## Test

```bash
make test
```

## Run the demo eval set

```bash
make eval
```

Detailed results are written to `evals/latest-results.json`.

## Hackathon non-goals

No auth, no Postgres, no Supabase, no PDF OCR, no graph DB, no user accounts, no production-scale ingestion pipeline.
