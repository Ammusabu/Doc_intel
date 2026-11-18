"""
Reciprocal Rank Fusion (RRF) — combine dense and keyword rankings.
score(d) = sum_i  1 / (k + rank_i(d)),  k=60 by convention.
"""
from __future__ import annotations

from collections import defaultdict


def reciprocal_rank_fusion(
    dense_results: list[dict],
    keyword_results: list[dict],
    *,
    k: int = 60,
) -> list[dict]:
    by_id: dict = {}

    for rank, hit in enumerate(dense_results, start=1):
        cid = hit["chunk_id"]
        by_id.setdefault(cid, {
            "chunk_id": cid,
            "document_id": hit["document_id"],
            "document_title": hit["document_title"],
            "chunk_index": hit["chunk_index"],
            "page_number": hit["page_number"],
            "content": hit["content"],
            "dense_score": None,
            "keyword_score": None,
            "rrf_score": 0.0,
        })
        by_id[cid]["dense_score"] = hit.get("dense_score")
        by_id[cid]["rrf_score"] += 1.0 / (k + rank)

    for rank, hit in enumerate(keyword_results, start=1):
        cid = hit["chunk_id"]
        by_id.setdefault(cid, {
            "chunk_id": cid,
            "document_id": hit["document_id"],
            "document_title": hit["document_title"],
            "chunk_index": hit["chunk_index"],
            "page_number": hit["page_number"],
            "content": hit["content"],
            "dense_score": None,
            "keyword_score": None,
            "rrf_score": 0.0,
        })
        by_id[cid]["keyword_score"] = hit.get("keyword_score")
        by_id[cid]["rrf_score"] += 1.0 / (k + rank)

    return sorted(by_id.values(), key=lambda x: x["rrf_score"], reverse=True)
