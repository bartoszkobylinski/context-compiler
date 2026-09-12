from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any

from .models import Document
from .verifier import verify_answer


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def document_fingerprint(doc: Document) -> str:
    """Fingerprint the exact approved source state used by a released answer."""
    snapshot = {
        "id": doc.id,
        "title": doc.title,
        "body": doc.body,
        "published_at": doc.published_at.isoformat() if doc.published_at else None,
        "valid_from": doc.valid_from.isoformat() if doc.valid_from else None,
        "valid_to": doc.valid_to.isoformat() if doc.valid_to else None,
        "supersedes": doc.supersedes,
        "authority": doc.authority,
        "domains": doc.domains,
        "references": doc.references,
    }
    return _sha256(snapshot)


def create_certificate(
    answer: dict[str, Any],
    corpus: dict[str, Document],
    query_date: date | None,
) -> dict[str, Any] | None:
    """Create a tamper-evident release receipt for a deterministically verified answer.

    This proves integrity against the current approved corpus snapshot; it is not a
    cryptographic claim that the underlying documents are objectively true.
    """
    if answer.get("status") != "SUPPORTED":
        return None

    verification = verify_answer(answer, corpus, query_date)
    if not verification["complete"]:
        return None

    source_ids = sorted({str(claim.get("source_id", "")) for claim in answer.get("claims", []) if claim.get("source_id")})
    sources = []
    for source_id in source_ids:
        doc = corpus.get(source_id)
        if doc is None:
            continue
        sources.append({
            "source_id": source_id,
            "fingerprint": document_fingerprint(doc),
        })

    payload = {
        "version": 1,
        "kind": "evidence-release-receipt",
        "query_date": query_date.isoformat() if query_date else None,
        "answer": answer.get("answer", ""),
        "claims": answer.get("claims", []),
        "sources": sources,
        "verification": {
            "claims_passed": len(verification.get("checks", [])),
            "claims_total": len(verification.get("checks", [])),
            "answer_coverage_complete": bool(verification.get("coverage", {}).get("complete")),
        },
    }
    certificate_hash = _sha256(payload)
    return {**payload, "certificate_hash": certificate_hash}


def verify_certificate(certificate: dict[str, Any], corpus: dict[str, Document]) -> dict[str, Any]:
    """Verify a release receipt without calling an LLM."""
    supplied_hash = str(certificate.get("certificate_hash", ""))
    payload = {key: value for key, value in certificate.items() if key != "certificate_hash"}
    recomputed_hash = _sha256(payload)
    issues: list[str] = []

    if not supplied_hash or supplied_hash != recomputed_hash:
        issues.append("certificate payload hash mismatch")

    source_map = {item.get("source_id"): item.get("fingerprint") for item in certificate.get("sources", []) if isinstance(item, dict)}
    for source_id, expected in source_map.items():
        doc = corpus.get(str(source_id))
        if doc is None:
            issues.append(f"source missing from approved corpus: {source_id}")
            continue
        actual = document_fingerprint(doc)
        if actual != expected:
            issues.append(f"source fingerprint changed: {source_id}")

    query_date_raw = certificate.get("query_date")
    query_date = date.fromisoformat(query_date_raw) if query_date_raw else None
    answer_bundle = {
        "status": "SUPPORTED",
        "answer": certificate.get("answer", ""),
        "claims": certificate.get("claims", []),
        "unresolved": [],
    }
    verification = verify_answer(answer_bundle, corpus, query_date)
    if not verification["complete"]:
        issues.extend(verification.get("missing", []))

    return {
        "valid": not issues,
        "certificate_hash": supplied_hash,
        "recomputed_hash": recomputed_hash,
        "issues": issues,
        "verification": verification,
        "model_call_required": False,
    }
