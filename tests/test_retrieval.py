from pathlib import Path

from backend.tools import load_corpus
from backend.baseline import retrieve_baseline

ROOT = Path(__file__).resolve().parents[1]
CORPUS = load_corpus(ROOT / "corpus")

QUESTION = "Can a contractor access customer data from a personal laptop using VPN?"


def test_naive_top3_prefers_surface_similar_current_guidance_over_historical_policy():
    hits = retrieve_baseline(CORPUS, QUESTION, top_k=3)
    ids = [hit["id"] for hit in hits]

    # The historical rule is deliberately phrased in older terminology (BYOD,
    # restricted client records, corporate tunnel). A one-shot similarity search
    # should therefore be vulnerable to missing it even though it is the rule
    # actually valid for the June 2025 query date.
    assert "security-policy-2024" not in ids


def test_current_policy_is_retrievable_for_same_surface_wording():
    hits = retrieve_baseline(CORPUS, QUESTION, top_k=5)
    ids = [hit["id"] for hit in hits]
    assert "security-policy-2025" in ids
