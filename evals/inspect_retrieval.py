from pathlib import Path

from backend.baseline import retrieve_baseline
from backend.tools import load_corpus

ROOT = Path(__file__).resolve().parents[1]
CORPUS = load_corpus(ROOT / "corpus")
QUESTION = "Can a contractor access customer data from a personal laptop using VPN?"


def main() -> None:
    print(QUESTION)
    print()
    for k in (1, 2, 3, 5, 8):
        hits = retrieve_baseline(CORPUS, QUESTION, top_k=k)
        print(f"top-{k}")
        for rank, hit in enumerate(hits, start=1):
            print(f"  {rank}. {hit['id']:<32} score={hit['score']}")
        print()

    top3 = [hit["id"] for hit in retrieve_baseline(CORPUS, QUESTION, top_k=3)]
    historical = "security-policy-2024"
    current = "security-policy-2025"

    print("TEMPORAL TRAP CHECK")
    print(f"historical rule in top-3: {historical in top3}")
    print(f"current rule in top-3:    {current in top3}")
    if historical not in top3 and current in top3:
        print("PASS — one-shot similarity is exposed to the intended temporal failure mode.")
    else:
        print("WARN — retrieval ranking does not currently expose the intended temporal trap strongly enough.")


if __name__ == "__main__":
    main()
