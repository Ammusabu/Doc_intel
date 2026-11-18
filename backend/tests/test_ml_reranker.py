"""
Reranker tests — prove real ranking behavior, not just shape.

The key test: given the query "what is the tax filing deadline", the passage about
tax deadlines must score higher than the passage about dog training. This proves
the cross-encoder understands joint query-document relevance.
"""
from app.ml.reranker import Reranker


def test_score_returns_one_float_per_document():
    rk = Reranker.load()
    scores = rk.score("query", ["doc one", "doc two", "doc three"])
    assert len(scores) == 3
    assert all(isinstance(s, float) for s in scores)


def test_relevant_document_scores_higher_than_irrelevant():
    rk = Reranker.load()
    query = "What is the quarterly tax filing deadline?"
    docs = [
        "The quarterly tax filing deadline is April 15th each year.",
        "Dogs require daily exercise and a balanced diet.",
        "Photosynthesis converts sunlight into chemical energy.",
    ]
    scores = rk.score(query, docs)
    # the tax passage must outscore both unrelated passages
    assert scores[0] > scores[1], f"tax={scores[0]:.3f} dog={scores[1]:.3f}"
    assert scores[0] > scores[2], f"tax={scores[0]:.3f} photosynthesis={scores[2]:.3f}"


def test_rerank_sorts_descending_and_adds_score():
    rk = Reranker.load()
    query = "how do I reset my password"
    candidates = [
        {"id": 1, "content": "Bananas are rich in potassium."},
        {"id": 2, "content": "Click 'forgot password' to reset your login credentials."},
        {"id": 3, "content": "The Eiffel Tower is 330 meters tall."},
    ]
    ranked = rk.rerank(query, candidates, top_k=3)
    assert len(ranked) == 3
    assert ranked[0]["id"] == 2, "relevant doc must be ranked #1"
    assert all("rerank_score" in c for c in ranked)
    scores = [c["rerank_score"] for c in ranked]
    assert scores == sorted(scores, reverse=True)


def test_empty_candidates():
    rk = Reranker.load()
    assert rk.score("q", []) == []
    assert rk.rerank("q", []) == []
