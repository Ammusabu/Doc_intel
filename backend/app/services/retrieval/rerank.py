"""Cross-encoder reranking of hybrid search candidates."""
from __future__ import annotations

from app.ml.reranker import Reranker


def rerank_results(
    reranker: Reranker,
    query: str,
    candidates: list[dict],
    top_k: int = 10,
) -> list[dict]:
    if not candidates:
        return []
    texts = [c["content"] for c in candidates]
    scores = reranker.score(query, texts)
    enriched = [
        {**c, "rerank_score": float(s), "final_rank": 0}
        for c, s in zip(candidates, scores)
    ]
    enriched.sort(key=lambda x: x["rerank_score"], reverse=True)
    for i, item in enumerate(enriched, start=1):
        item["final_rank"] = i
    return enriched[:top_k]
