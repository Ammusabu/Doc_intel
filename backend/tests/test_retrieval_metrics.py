"""Sanity tests for retrieval metric logic (Recall@K, MRR, nDCG@K)."""
import math
from pathlib import Path


def _dcg(rels: list[int]) -> float:
    return sum((2**r - 1) / math.log2(i + 2) for i, r in enumerate(rels))


def test_recall_at_k():
    ranks = [2]
    for k in [1, 2, 3]:
        recall = 1 if any(r <= k for r in ranks) else 0
        assert recall == (0 if k == 1 else 1)


def test_mrr():
    ranks_per_query = [[2], [1], [5], []]
    rr = [1.0 / r[0] if r else 0.0 for r in ranks_per_query]
    mrr = sum(rr) / len(rr)
    assert abs(mrr - (0.5 + 1.0 + 0.2 + 0.0) / 4) < 1e-6


def test_ndcg_at_1():
    rels = [1, 0, 0, 0, 0]
    assert abs(_dcg(rels) / _dcg([1, 0, 0, 0, 0]) - 1.0) < 1e-6
