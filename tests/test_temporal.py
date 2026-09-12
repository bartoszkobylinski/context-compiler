from datetime import date
from pathlib import Path

from backend.tools import load_corpus
from backend.temporal import valid_at

ROOT = Path(__file__).resolve().parents[1]
CORPUS = load_corpus(ROOT / "corpus")


def test_2024_policy_valid_in_june_2025():
    assert valid_at(CORPUS["security-policy-2024"], date(2025, 6, 10))


def test_2025_policy_not_yet_valid_in_june_2025():
    assert not valid_at(CORPUS["security-policy-2025"], date(2025, 6, 10))


def test_2025_policy_valid_in_august_2025():
    assert valid_at(CORPUS["security-policy-2025"], date(2025, 8, 10))
