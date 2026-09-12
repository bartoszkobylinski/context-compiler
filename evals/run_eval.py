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


def main() -> None:
    rows = []
    for case in CASES:
        when = date.fromisoformat(case["query_date"]) if case.get("query_date") else None
        print(f"\n=== {case['id']} ===")
        print(case["question"])
        print(f"query date: {when} | expected: {case['expected']}")

        baseline = answer_baseline(CORPUS, case["question"], when, top_k=3)
        compiler = run_compiler(CORPUS, case["question"], when)

        print("\nBASELINE")
        print(compact(baseline["answer"], 500))
        print("hits:", ", ".join(hit["id"] for hit in baseline.get("hits", [])))

        print("\nCONTEXT COMPILER")
        print(f"status: {compiler.get('status')} | steps: {compiler.get('steps')}")
        print(compact(compiler.get("answer", ""), 500))
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
                "baseline": baseline,
                "compiler": compiler,
            }
        )

    output = ROOT / "evals" / "latest-results.json"
    output.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved detailed results to {output}")


if __name__ == "__main__":
    main()
