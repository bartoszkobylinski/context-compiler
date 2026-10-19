# context-compiler — Roadmap

Last reviewed: 2026-10-19 · Reviewed against: 871702d
Product: standalone · Product roadmap: this file

A hackathon MVP that contrasts one-shot RAG with an evidence-building loop: declare evidence
requirements, retrieve iteratively, check version, validity date and authority, verify every
claim deterministically against a verbatim quote, then answer or return `UNKNOWN` (`README.md`).
All 208 commits on `main` are dated 2026-09-12; there are no issues and two merged PRs. No roadmap,
TODO or ADR document exists in the repository, so Next and Later have no owner-written source.

Explicit non-goals (`README.md` § Hackathon non-goals): Postgres, Supabase, PDF OCR, graph DB,
user accounts, production-scale ingestion. ("No auth" is also listed, but an optional HTTP Basic
gate shipped in #2 — see Done.)

## Now
- (none recorded) — finished hackathon artefact; the repository is archived (owner, 2026-10-19)

## Next
- (none recorded)

## Later
- (none recorded)

## Done
- Public demo taken down — `hackathon.bartoszkobylinski.com` (PR #2) no longer resolves in DNS (checked 2026-10-19)
Most recent first. Everything below landed on 2026-09-12.

Verifier and agent loop
- Dependency references exposed in retrieval hits — `871702d`
- Larger recovery budget for the evidence repair loop — `86a35dd`
- Source and document identifiers allowed in claims and quote-coverage checks — `4b87dcd`, `6dd6d9e`
- Reject source-backed claims that overreach their quoted evidence — `473a125`
- Evidence contract: deterministic requirement closure, release gated on closure, candidate plans
  with validated evidence links, coverage checked against mapped claims — `0654041`, `72db7ac`,
  `3a25ba1`, `789cd31`, `a36a292`; code `backend/verifier.py`, `backend/agent.py`
- Answer coverage enforced by verified claims; grounded answer prose; compiler token usage tracked
  — `d4b34ab`, `a8904d0`
- Verifier failures loop back into retrieval; verbatim evidence quotes required — `9e7ef58`, `da43477`
- Evidence requirements as the first, explicit agent step — `25824fb`, `932f72c`
- Anthropic tool-use evidence loop — `894e696`; tools `backend/tools/`
- Deterministic temporal validity engine — `e2ed52b`; code `backend/temporal.py`

Baseline (control)
- Two-pass RAG as the stronger control, labelled and shown honestly — `7e634fc`, `88220e6`,
  `76c24b6`, `beede8a`
- One-shot RAG as a best-effort baseline without forced abstention; output budget raised and stop
  reason exposed — `2e099db`, `2bb7071`
- Realistic chunk-only one-shot baseline; token usage exposed — `4e83021`, `ff46d09`; code
  `backend/baseline.py`

Receipts and challenge mode
- Deterministic evidence release receipts with create/verify endpoints and integrity tests —
  `66df3bb`, `b4cb5a5`, `c4d8fae`; code `backend/certificate.py`, `tests/test_certificate.py`
- Deterministic adversarial challenge generator, endpoint and UI, each challenge isolating one
  verifier failure — `dfcbb7a`, `b8c0599`, `263d306`, `ebf48bd`; code `backend/challenge.py`

Demo corpus and cases
- Five operational shipping conflict demos replace the policy demos as the default (`/demo-cases`)
  — `cb16ea2`, `5ad849d`, `6ecd331`; documents in `corpus/` (orders, SKUs, carrier, packaging,
  cold chain, live animal, fragile, high value, remote address, weather, customs)
- Policy demo corpus: temporal flip (security policy 2024/2025), multi-hop AI policy chain,
  knowledge boundary, adversarial remote-access decoy — `4d38727`…`0845356`, `f343589`, `fe0c6ce`

Frontend
- Side-by-side demo UI with live streamed compiler and baseline events, execution flow, self-repair
  loop, proof panel, receipts and shipping operations console — `1307754`, `c64fe96`, `90dd6a8`,
  `f34bc48`, `23d997a`, `75ef6e6`; code `frontend/`
- Continuous elapsed time in live activity; misleading pulse indicator removed — `56d2cad`, `2c213d3`

Evaluation
- Live Anthropic API evaluation on `claude-sonnet-5` over 4 cases, raw results committed —
  `8bae498`, `b75e1c9`; `evals/latest-results.json`, `evals/API_EVAL_SUMMARY.md`
- `UNKNOWN` scored by status instead of a prose token — `9f4d05e`
- Machine-scoreable eval cases and comparison runner; offline retrieval inspection — `1b66e86`,
  `888b26c`, `efca035`; `evals/`
- Zero-cost retrieval diagnostics endpoint — `60b38a1`

Deployment and tooling
- Frontend served by the app, optional HTTP Basic gate, narrowed CORS, systemd unit — #2 (merge
  `0682907`); code `backend/gate.py`, `deploy/context-compiler.service`
- Gate answers 401 instead of 500 for non-ASCII credentials — `112c3bc`
- Run on `claude-sonnet-5`, move to a `uv` toolchain — #1 (`c97506a`)
- Dedicated demo ports 4865/4866 — `8909be5`, `70794b5`
- CI: offline tests plus the retrieval-trap inspection — `1298f83`, `42dd890`;
  `.github/workflows/tests.yml`
- Two-minute demo script — `1b82e43`; `DEMO_SCRIPT.md`

## Unverified
- Branch `fix/agent-empty-turn` (3 commits, no PR, 2026-09-12: keep the run alive on an empty step `9495f89`, `max_tokens` back to 8000 `b4e5b74`, verifier coverage floor 0.45 → 0.30 `2ccd941`) — kept as reference, never merged (owner, 2026-10-19).
- "Verified decision dataset" / "TRAINING-READY" stage (`2a6898a`, `frontend/certificate-ui.js:51-58`,
  `frontend/flow-ui.js:8`) — shown in the UI only; no backend code writes or exports a dataset, and
  no document says whether it is planned.
- Eval coverage of the shipping demos — `evals/cases.json` holds only the 4 policy cases; the 5
  default shipping cases in `backend/main.py` `/demo-cases` have no recorded eval. No plan states
  whether they should.
- Current eval score — `evals/API_EVAL_SUMMARY.md` reports "Baseline 3/4 · Context Compiler 3/4"
  (generated 2026-09-12T10:47:54Z), while the later `b75e1c9` ("Record verified 4-of-4 compiler
  API eval") updated only `evals/latest-results.json` (compiler_pass true for all 4). The summary
  was not regenerated, and neither file reflects verifier changes made after it.

## Sources
- `README.md`, `DEMO_SCRIPT.md`, `frontend/README.md`, `evals/API_EVAL_SUMMARY.md`,
  `evals/cases.json`, `evals/latest-results.json`, `Makefile`, `.env.example`,
  `.github/workflows/tests.yml`, `deploy/context-compiler.service`, `backend/main.py`,
  `backend/gate.py`, `frontend/certificate-ui.js`, `frontend/flow-ui.js`
- `git log` of `main` (208 commits) and of `origin/fix/agent-empty-turn`
- `gh issue list -R bartoszkobylinski/context-compiler --state all -L 200` (empty)
- `gh pr list -R bartoszkobylinski/context-compiler --state all -L 200` (#1, #2, both merged)
- No CLAUDE.md, AGENTS.md, roadmap, TODO or ADR files exist in the repository.
