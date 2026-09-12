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
        {"status": "UNKNOWN", "answer": "UNKNOWN", "claims": [], "unresolved": ["No policy addresses spouse meals."]},
        CORPUS,
        date(2025, 8, 10),
    )
    assert result["complete"] is True
