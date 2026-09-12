from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from backend.agent import run_compiler
from backend.baseline import answer_baseline
from backend.tools import load_corpus

ROOT = Path(__file__).resolve().parents[1]
CORPUS = load_corpus(ROOT / "corpus")
CASES = json.loads((ROOT / "evals" / "cases.json").read_text())


def compact(value: str, width: int = 120) -> str:
    value = " ".join(value.split())
    return value if len(value) <= width else value[: width - 1] + "…"


def _answer_matches(case: dict, answer: str) -> bool:
    text = (answer or "").lower()
    all_terms = [term.lower() for term in case.get("answer_all", [])]
    any_terms = [term.lower() for term in case.get("answer_any", [])]
    return all(term in text for term in all_terms) and (
        not any_terms or any(term in text for term in any_terms)
    )


def _compiler_sources(compiler: dict) -> set[str]:
    return {
        claim.get("source_id")
        for claim in compiler.get("claims", [])
        if claim.get("source_id")
    }


def _compiler_passes(case: dict, compiler: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    expected_status = case.get("expected_status")
    if expected_status and compiler.get("status") != expected_status:
        reasons.append(f"status={compiler.get('status')} expected={expected_status}")

    if not _answer_matches(case, compiler.get("answer", "")):
        reasons.append("answer shape did not match expected outcome")

    required = set(case.get("required_sources", []))
    missing_sources = required - _compiler_sources(compiler)
    if missing_sources:
        reasons.append(f"missing required sources: {sorted(missing_sources)}")

    verification = compiler.get("verification", {})
    if expected_status == "SUPPORTED" and verification and not verification.get("complete", False):
        reasons.append("deterministic verification incomplete")

    return not reasons, reasons


def main() -> None:
    rows = []
    baseline_passes = 0
    compiler_passes = 0

    for case in CASES:
        when = date.fromisoformat(case["query_date"]) if case.get("query_date") else None
        print(f"\n=== {case['id']} ===")
        print(case.get("label", ""))
        print(case["question"])
        print(f"query date: {when} | expected: {case['expected']}")

        baseline = answer_baseline(CORPUS, case["question"], when, top_k=3)
        compiler = run_compiler(CORPUS, case["question"], when)

        baseline_ok = _answer_matches(case, baseline.get("answer", ""))
        compiler_ok, compiler_reasons = _compiler_passes(case, compiler)
        baseline_passes += int(baseline_ok)
        compiler_passes += int(compiler_ok)

        print("\nBASELINE", "PASS" if baseline_ok else "FAIL")
        print(compact(baseline["answer"], 500))
        print("hits:", ", ".join(hit["id"] for hit in baseline.get("hits", [])))

        print("\nCONTEXT COMPILER", "PASS" if compiler_ok else "FAIL")
        print(f"status: {compiler.get('status')} | steps: {compiler.get('steps')}")
        print(compact(compiler.get("answer", ""), 500))
        if compiler_reasons:
            print("reasons:", "; ".join(compiler_reasons))
        verification = compiler.get("verification", {})
        checks = verification.get("checks", [])
        if checks:
            print(f"verification: {sum(1 for c in checks if c.get('ok'))}/{len(checks)} claims passed")
        else:
            print("verification: no claims released")

        rows.append(
            {
                "id": case["id"],
                "question": case["question"],
                "query_date": case.get("query_date"),
                "expected": case["expected"],
                "baseline_pass": baseline_ok,
                "compiler_pass": compiler_ok,
                "compiler_fail_reasons": compiler_reasons,
                "baseline": baseline,
                "compiler": compiler,
            }
        )

    total = len(CASES)
    print("\n=== SCORE ===")
    print(f"Baseline:         {baseline_passes}/{total}")
    print(f"Context Compiler: {compiler_passes}/{total}")

    output = ROOT / "evals" / "latest-results.json"
    output.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved detailed results to {output}")


if __name__ == "__main__":
    main()
