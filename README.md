# Context Compiler

Hackathon MVP: turn retrieval from a one-shot similarity lookup into an evidence-building loop.

## Core idea

Traditional RAG:

`question -> top-k similarity -> model -> answer`

Context Compiler:

`question -> evidence requirements -> iterative retrieval -> temporal/authority checks -> claim verification -> answer or UNKNOWN`

## Demo scenario

Primary security question:

> Can a contractor access customer data from a personal laptop using VPN on June 10, 2025?

Expected answer: **YES**, because the 2024 security policy is still valid on that date, but only with VPN + full-disk encryption.

Same question on August 10, 2025:

Expected answer: **NO**, because the 2025 policy is effective from July 1, 2025 and requires a company-managed device.

Third case:

> Can a contractor expense their spouse's breakfast?

Expected answer: **UNKNOWN**.

## Architecture

- `frontend/` — minimal demo UI (planned)
- `backend/` — FastAPI + baseline RAG + Context Compiler loop
- `backend/tools/` — retrieval, versioning, temporal checks
- `corpus/` — curated Markdown corpus with YAML metadata
- `evals/` — deterministic demo cases
- `tests/` — temporal and corpus tests

## Definition of done

1. Baseline RAG can produce a plausible but temporally wrong answer on at least one case.
2. Context Compiler resolves the correct policy valid at the query date.
3. Context Compiler returns `UNKNOWN` when evidence is insufficient.
4. UI visibly shows the evidence-building actions.

## Non-goals for hackathon

No auth, no Postgres, no Supabase, no PDF OCR, no graph DB, no user accounts, no production deployment requirements.
