from datetime import date
from pathlib import Path

from backend.challenge import make_challenge_candidate, reason_codes
from backend.tools import load_corpus

ROOT = Path(__file__).resolve().parents[1]
CORPUS = load_corpus(ROOT / "corpus")
QUESTION = "Can a contractor access customer data from a personal laptop using VPN?"
WHEN = date(2025, 6, 10)


def test_future_policy_is_blocked_temporally():
    challenge = make_challenge_candidate(CORPUS, QUESTION, WHEN, "future_policy")
    assert challenge["blocked"] is True
    assert "TEMPORAL_INVALID" in reason_codes(challenge["verification"])


def test_corrupt_quote_is_blocked():
    challenge = make_challenge_candidate(CORPUS, QUESTION, WHEN, "corrupt_quote")
    assert challenge["blocked"] is True
    assert "QUOTE_MISMATCH" in reason_codes(challenge["verification"])


def test_unsupported_claim_is_blocked_by_answer_coverage():
    challenge = make_challenge_candidate(CORPUS, QUESTION, WHEN, "unsupported_claim")
    assert challenge["blocked"] is True
    assert "ANSWER_COVERAGE" in reason_codes(challenge["verification"])
