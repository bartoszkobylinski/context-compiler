from datetime import date
from pathlib import Path

from backend.certificate import create_certificate, verify_certificate
from backend.tools import load_corpus


ROOT = Path(__file__).resolve().parents[1]
CORPUS = load_corpus(ROOT / "corpus")


def _supported_answer():
    return {
        "status": "SUPPORTED",
        "answer": "Customer data may only be accessed from company-managed devices.",
        "claims": [
            {
                "claim": "Customer data may only be accessed from company-managed devices.",
                "source_id": "security-policy-2025",
                "section": "4.2 Customer data access",
                "quote": "Customer data may only be accessed from company-managed devices.",
            }
        ],
        "unresolved": [],
    }


def test_certificate_round_trip_without_model():
    cert = create_certificate(_supported_answer(), CORPUS, date(2025, 8, 10))
    assert cert is not None
    result = verify_certificate(cert, CORPUS)
    assert result["valid"] is True
    assert result["model_call_required"] is False


def test_tampered_quote_invalidates_certificate():
    cert = create_certificate(_supported_answer(), CORPUS, date(2025, 8, 10))
    assert cert is not None
    cert["claims"][0]["quote"] += " [tampered]"
    result = verify_certificate(cert, CORPUS)
    assert result["valid"] is False
    assert "certificate payload hash mismatch" in result["issues"]


def test_wrong_date_cannot_receive_certificate():
    cert = create_certificate(_supported_answer(), CORPUS, date(2025, 6, 10))
    assert cert is None
