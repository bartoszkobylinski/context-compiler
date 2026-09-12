from datetime import date
from pathlib import Path

from backend.tools import load_corpus
from backend.verifier import verify_answer

ROOT = Path(__file__).resolve().parents[1]
CORPUS = load_corpus(ROOT / "corpus")


def test_supported_claim_requires_exact_quote_and_valid_source():
    answer = {
        "status": "SUPPORTED",
        "answer": "No, a managed device is required.",
        "claims": [
            {
                "claim": "Customer data requires a company-managed device.",
                "source_id": "security-policy-2025",
                "section": "4.2",
                "quote": "Customer data may only be accessed from company-managed devices.",
            }
        ],
        "unresolved": [],
    }
    result = verify_answer(answer, CORPUS, date(2025, 8, 10))
    assert result["complete"] is True
    assert result["coverage"]["complete"] is True


def test_future_policy_is_rejected_for_past_query_date():
    answer = {
        "status": "SUPPORTED",
        "answer": "No, a managed device is required.",
        "claims": [
            {
                "claim": "Customer data requires a company-managed device.",
                "source_id": "security-policy-2025",
                "quote": "Customer data may only be accessed from company-managed devices.",
            }
        ],
        "unresolved": [],
    }
    result = verify_answer(answer, CORPUS, date(2025, 6, 10))
    assert result["complete"] is False
    assert any("not valid" in item for item in result["missing"])


def test_paraphrased_quote_is_rejected():
    answer = {
        "status": "SUPPORTED",
        "answer": "No.",
        "claims": [
            {
                "claim": "A managed device is required.",
                "source_id": "security-policy-2025",
                "quote": "A company-managed laptop is required for all customer data.",
            }
        ],
        "unresolved": [],
    }
    result = verify_answer(answer, CORPUS, date(2025, 8, 10))
    assert result["complete"] is False
    assert any("verbatim" in item for item in result["missing"])


def test_unknown_requires_explicit_gap():
    result = verify_answer(
        {
            "status": "UNKNOWN",
            "answer": "The corpus does not establish whether this expense is allowed.",
            "claims": [],
            "unresolved": ["No policy addresses spouse meals."],
        },
        CORPUS,
        date(2025, 8, 10),
    )
    assert result["complete"] is True


def test_unsupported_material_sentence_is_rejected_even_when_claims_verify():
    answer = {
        "status": "SUPPORTED",
        "answer": (
            "Customer data is Confidential and external AI providers require explicit approval. "
            "General-purpose AI assistants are typically not on the approved list."
        ),
        "claims": [
            {
                "claim": "Customer data is classified as Confidential.",
                "source_id": "data-classification-policy",
                "quote": "Customer data is classified as Confidential.",
            },
            {
                "claim": "Confidential data must not be sent to external AI providers unless the provider is explicitly approved for Confidential data.",
                "source_id": "ai-security-addendum",
                "quote": "Confidential data must not be sent to external AI providers unless the provider is explicitly approved for Confidential data.",
            },
        ],
        "unresolved": [],
    }
    result = verify_answer(answer, CORPUS, date(2025, 8, 10))
    assert result["complete"] is False
    assert result["coverage"]["complete"] is False
    assert any("not covered" in item for item in result["missing"])


def test_requirement_closure_requires_claims_that_cover_requirement_text():
    requirement = "Whether customer data requires a company-managed device"
    answer = {
        "status": "SUPPORTED",
        "decision": "A managed device is required.",
        "recommendation": "",
        "answer": "Customer data requires a company-managed device.",
        "claims": [
            {
                "claim": "Customer data requires a company-managed device.",
                "source_id": "security-policy-2025",
                "quote": "Customer data may only be accessed from company-managed devices.",
            }
        ],
        "requirement_closure": [
            {"requirement": requirement, "status": "RESOLVED", "claim_indices": [1]}
        ],
        "plan_candidates": [],
        "unresolved": [],
    }
    result = verify_answer(
        answer,
        CORPUS,
        date(2025, 8, 10),
        declared_requirements=[requirement],
    )
    assert result["complete"] is True
    assert result["requirement_closure"]["checks"][0]["coverage_score"] >= 0.45


def test_requirement_closure_rejects_valid_but_unrelated_claim_mapping():
    requirement = "Whether shipment weight limit allows a large parcel"
    answer = {
        "status": "SUPPORTED",
        "decision": "A managed device is required.",
        "recommendation": "",
        "answer": "Customer data requires a company-managed device.",
        "claims": [
            {
                "claim": "Customer data requires a company-managed device.",
                "source_id": "security-policy-2025",
                "quote": "Customer data may only be accessed from company-managed devices.",
            }
        ],
        "requirement_closure": [
            {"requirement": requirement, "status": "RESOLVED", "claim_indices": [1]}
        ],
        "plan_candidates": [],
        "unresolved": [],
    }
    result = verify_answer(
        answer,
        CORPUS,
        date(2025, 8, 10),
        declared_requirements=[requirement],
    )
    assert result["complete"] is False
    closure_check = result["requirement_closure"]["checks"][0]
    assert closure_check["ok"] is False
    assert "weight" in closure_check["missing_qualifiers"]
    assert any("requirement not closed" in item for item in result["missing"])
