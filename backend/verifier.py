from __future__ import annotations

import re
from datetime import date
from typing import Any

from .models import Document
from .temporal import valid_at


_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "because", "but", "by", "can",
    "do", "does", "for", "from", "has", "have", "if", "in", "is", "it", "may",
    "must", "no", "not", "of", "on", "only", "or", "so", "that", "the", "their",
    "this", "to", "use", "uses", "using", "was", "were", "when", "with", "yes",
}

# Decision-critical qualifiers that should not disappear when a requirement is marked
# RESOLVED. This stays deliberately small and deterministic; it is not an entailment model.
_REQUIREMENT_QUALIFIERS = {
    "next",
    "earliest",
    "latest",
    "weight",
    "size",
    "dimension",
    "signature",
    "insurance",
    "packaging",
    "temperature",
    "weather",
    "cutoff",
    "supervisor",
}


def _terms(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    normalized: set[str] = set()
    for token in tokens:
        if token in _STOPWORDS or len(token) <= 2:
            continue
        for suffix in ("ing", "ed", "es", "s"):
            if token.endswith(suffix) and len(token) - len(suffix) >= 4:
                token = token[: -len(suffix)]
                break
        normalized.add(token)
    return normalized


def _material_sentences(text: str) -> list[str]:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]
    return [sentence for sentence in sentences if len(_terms(sentence)) >= 3]


def _answer_coverage(answer_text: str, claims: list[dict[str, Any]]) -> dict[str, Any]:
    claim_terms = [_terms(str(claim.get("claim", ""))) for claim in claims]
    checks: list[dict[str, Any]] = []
    uncovered: list[str] = []
    for sentence in _material_sentences(answer_text):
        terms = _terms(sentence)
        best_index = None
        best_score = 0.0
        for index, candidate in enumerate(claim_terms):
            if not candidate:
                continue
            overlap = len(terms & candidate)
            score = overlap / max(1, min(len(terms), len(candidate)))
            if score > best_score:
                best_score = score
                best_index = index
        covered = best_score >= 0.45
        checks.append({
            "sentence": sentence,
            "covered": covered,
            "claim_index": None if best_index is None else best_index + 1,
            "score": round(best_score, 3),
        })
        if not covered:
            uncovered.append(sentence)
    return {"complete": not uncovered, "checks": checks, "uncovered": uncovered}


def _requirement_text(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("requirement") or value.get("text") or value.get("id") or "").strip()
    return str(value or "").strip()


def _validate_claim_indices(indices: Any, claim_checks: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if not isinstance(indices, list) or not indices:
        return ["no supporting claim indices"]
    for claim_index in indices:
        if not isinstance(claim_index, int) or claim_index < 1 or claim_index > len(claim_checks):
            errors.append(f"invalid claim index {claim_index!r}")
            continue
        if not claim_checks[claim_index - 1].get("ok"):
            errors.append(f"claim {claim_index} did not pass verification")
    return errors


def _requirement_claim_coverage(
    requirement: str,
    indices: Any,
    claim_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Deterministically check that mapped claims actually cover the requirement.

    Claim-index validity alone is not enough: a valid but unrelated claim must not close
    an evidence requirement. We therefore compare the requirement with the union of the
    mapped verified claim texts and preserve a small set of decision-critical qualifiers
    such as `next`, `earliest`, `weight`, `signature`, or `temperature`.

    This is intentionally lexical and conservative. It is a release guard, not a semantic
    theorem prover. A low score causes another retrieval/repair turn or an UNKNOWN result.
    """
    if not isinstance(indices, list) or not indices:
        return {"covered": False, "score": 0.0, "missing_qualifiers": [], "evidence_terms": []}

    evidence_terms: set[str] = set()
    for claim_index in indices:
        if not isinstance(claim_index, int) or claim_index < 1 or claim_index > len(claim_checks):
            continue
        check = claim_checks[claim_index - 1]
        if not check.get("ok"):
            continue
        evidence_terms |= _terms(str(check.get("claim", "")))

    requirement_terms = _terms(requirement)
    if not requirement_terms:
        return {"covered": True, "score": 1.0, "missing_qualifiers": [], "evidence_terms": sorted(evidence_terms)}

    overlap = requirement_terms & evidence_terms
    score = len(overlap) / max(1, len(requirement_terms))

    required_qualifiers = requirement_terms & _REQUIREMENT_QUALIFIERS
    missing_qualifiers = sorted(required_qualifiers - evidence_terms)

    # Temporal validity is verified independently on every mapped claim, so words such as
    # "valid" or an ISO query date are intentionally not hard lexical anchors here.
    covered = score >= 0.45 and not missing_qualifiers
    return {
        "covered": covered,
        "score": round(score, 3),
        "missing_qualifiers": missing_qualifiers,
        "evidence_terms": sorted(evidence_terms),
    }


def _verify_requirement_closure(
    answer: dict[str, Any],
    declared_requirements: list[Any] | None,
    claim_checks: list[dict[str, Any]],
    require_all: bool,
) -> dict[str, Any]:
    declared = [_requirement_text(x) for x in (declared_requirements or [])]
    declared = [x for x in declared if x]
    rows = answer.get("requirement_closure", [])
    if not isinstance(rows, list):
        rows = []

    by_requirement: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        requirement = _requirement_text(row.get("requirement"))
        if requirement and requirement not in by_requirement:
            by_requirement[requirement] = row

    checks: list[dict[str, Any]] = []
    missing: list[str] = []
    resolved = 0

    for requirement in declared:
        row = by_requirement.get(requirement)
        errors: list[str] = []
        status = str((row or {}).get("status", "MISSING")).upper()
        claim_indices = (row or {}).get("claim_indices", [])
        semantic = {"covered": False, "score": 0.0, "missing_qualifiers": [], "evidence_terms": []}

        if row is None:
            errors.append("no closure entry")
        elif require_all and status != "RESOLVED":
            errors.append(f"status is {status}, expected RESOLVED")
        elif status == "RESOLVED":
            errors.extend(_validate_claim_indices(claim_indices, claim_checks))
            if not errors:
                semantic = _requirement_claim_coverage(requirement, claim_indices, claim_checks)
                if not semantic["covered"]:
                    detail = f"mapped claims cover only {semantic['score']:.0%} of requirement terms"
                    if semantic["missing_qualifiers"]:
                        detail += "; missing decision-critical terms: " + ", ".join(semantic["missing_qualifiers"])
                    errors.append(detail)

        ok = not errors and status == "RESOLVED"
        if ok:
            resolved += 1
        if errors and require_all:
            missing.append(f"requirement not closed: {requirement} ({'; '.join(errors)})")
        checks.append({
            "requirement": requirement,
            "status": status,
            "claim_indices": claim_indices if isinstance(claim_indices, list) else [],
            "coverage_score": semantic["score"],
            "missing_qualifiers": semantic["missing_qualifiers"],
            "ok": ok,
            "errors": errors,
        })

    return {
        "complete": (resolved == len(declared)) if require_all else True,
        "resolved": resolved,
        "total": len(declared),
        "checks": checks,
        "missing": missing,
    }


def _verify_plan_candidates(answer: dict[str, Any], claim_checks: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = answer.get("plan_candidates", [])
    if not isinstance(candidates, list):
        candidates = []
    checks: list[dict[str, Any]] = []
    missing: list[str] = []
    selected = 0
    for index, candidate in enumerate(candidates, start=1):
        if not isinstance(candidate, dict):
            missing.append(f"plan candidate {index}: invalid candidate object")
            continue
        name = str(candidate.get("name", "")).strip()
        status = str(candidate.get("status", "")).upper()
        claim_indices = candidate.get("claim_indices", [])
        errors: list[str] = []
        if not name:
            errors.append("name missing")
        if status not in {"SELECTED", "REJECTED"}:
            errors.append(f"invalid status {status!r}")
        else:
            errors.extend(_validate_claim_indices(claim_indices, claim_checks))
        if status == "SELECTED":
            selected += 1
        if errors:
            missing.append(f"plan candidate {index}: " + "; ".join(errors))
        checks.append({
            "name": name,
            "status": status,
            "claim_indices": claim_indices if isinstance(claim_indices, list) else [],
            "ok": not errors,
            "errors": errors,
        })

    recommendation = str(answer.get("recommendation", "")).strip()
    if candidates and recommendation and selected != 1:
        missing.append(f"plan candidates require exactly one SELECTED plan when recommendation is present; found {selected}")
    return {"complete": not missing, "checks": checks, "missing": missing, "selected": selected}


def verify_answer(
    answer: dict[str, Any],
    corpus: dict[str, Document],
    query_date: date | None,
    declared_requirements: list[Any] | None = None,
) -> dict[str, Any]:
    """Deterministic release gate for claims, answer coverage, evidence contract, and plan evidence links."""
    status = answer.get("status")
    claims = answer.get("claims", [])

    if status == "UNKNOWN":
        unresolved = answer.get("unresolved", [])
        closure = _verify_requirement_closure(answer, declared_requirements, [], require_all=False)
        return {
            "complete": bool(unresolved),
            "missing": [] if unresolved else ["UNKNOWN requires an explicit evidence gap"],
            "checks": [],
            "coverage": {"complete": True, "checks": [], "uncovered": []},
            "requirement_closure": closure,
            "plan_candidates": {"complete": True, "checks": [], "missing": [], "selected": 0},
        }

    if status == "CONFLICT":
        unresolved = answer.get("unresolved", [])
        closure = _verify_requirement_closure(answer, declared_requirements, [], require_all=False)
        return {
            "complete": bool(unresolved),
            "missing": [] if unresolved else ["CONFLICT requires an explicit unresolved conflict"],
            "checks": [],
            "coverage": {"complete": True, "checks": [], "uncovered": []},
            "requirement_closure": closure,
            "plan_candidates": {"complete": True, "checks": [], "missing": [], "selected": 0},
        }

    if status != "SUPPORTED":
        return {
            "complete": False,
            "missing": [f"unsupported final status: {status!r}"],
            "checks": [],
            "coverage": {"complete": False, "checks": [], "uncovered": []},
            "requirement_closure": {"complete": False, "resolved": 0, "total": len(declared_requirements or []), "checks": [], "missing": []},
            "plan_candidates": {"complete": False, "checks": [], "missing": [], "selected": 0},
        }

    if not claims:
        return {
            "complete": False,
            "missing": ["no material claims supplied"],
            "checks": [],
            "coverage": {"complete": False, "checks": [], "uncovered": []},
            "requirement_closure": {"complete": False, "resolved": 0, "total": len(declared_requirements or []), "checks": [], "missing": []},
            "plan_candidates": {"complete": False, "checks": [], "missing": [], "selected": 0},
        }

    missing: list[str] = []
    checks: list[dict[str, Any]] = []
    for idx, claim in enumerate(claims, start=1):
        claim_text = str(claim.get("claim", "")).strip()
        source_id = str(claim.get("source_id", "")).strip()
        quote = str(claim.get("quote", "")).strip()
        errors: list[str] = []
        if not claim_text:
            errors.append("claim text missing")
        doc = corpus.get(source_id) if source_id else None
        if doc is None:
            errors.append(f"unknown source_id {source_id!r}")
        else:
            if not quote:
                errors.append("supporting quote missing")
            elif quote not in doc.body:
                errors.append("supporting quote is not verbatim in cited source")
            if query_date is not None and not valid_at(doc, query_date):
                errors.append(f"source is not valid at {query_date.isoformat()}")
        checks.append({
            "claim": claim_text,
            "source_id": source_id,
            "quote": quote,
            "valid_at_query_time": None if doc is None or query_date is None else valid_at(doc, query_date),
            "ok": not errors,
            "errors": errors,
        })
        if errors:
            missing.append(f"claim {idx}: " + "; ".join(errors))

    coverage = _answer_coverage(str(answer.get("answer", "")), claims)
    for sentence in coverage["uncovered"]:
        missing.append(f"answer contains material text not covered by a declared claim: {sentence}")

    closure = _verify_requirement_closure(answer, declared_requirements, checks, require_all=True)
    missing.extend(closure["missing"])
    plans = _verify_plan_candidates(answer, checks)
    missing.extend(plans["missing"])

    return {
        "complete": not missing,
        "missing": missing,
        "checks": checks,
        "coverage": coverage,
        "requirement_closure": closure,
        "plan_candidates": plans,
    }
