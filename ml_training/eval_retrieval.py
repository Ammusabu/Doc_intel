"""
Retrieval quality metrics: Recall@K, MRR, nDCG@K.

Measures end-to-end quality via the live /search endpoint (dense + FTS + RRF + rerank).

Metrics:
- Recall@K: of all relevant chunks, how many appear in top-K? (our GT is 1 chunk/query → 0/1)
- MRR:      mean of 1/rank_of_first_relevant
- nDCG@K:   normalized DCG using binary relevance, ideal DCG = 1 at rank 1
"""
from __future__ import annotations

import httpx
import json
import math
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / "backend" / ".env")

BASE = "http://localhost:8000/api/v1"
QUERIES = Path(__file__).parent / "retrieval_queries.jsonl"
OUT = Path(__file__).parent / "eval_retrieval.json"
KS = [1, 3, 5, 10]


def _is_relevant(hit: dict, expected_title: str, fingerprint: str) -> bool:
    if hit["document_title"] != expected_title:
        return False
    return hit["content"][:40] == fingerprint


def _dcg(relevances: list[int]) -> float:
    return sum((2**rel - 1) / math.log2(i + 2) for i, rel in enumerate(relevances))


def main() -> None:
    if not QUERIES.exists():
        print(f"missing {QUERIES}; run build_retrieval_eval_set.py first")
        sys.exit(1)
    rows = [json.loads(l) for l in QUERIES.read_text().splitlines() if l.strip()]

    creds_path = QUERIES.parent / "eval_creds.json"
    if not creds_path.exists():
        print(f"missing {creds_path}; run build_retrieval_eval_set.py first")
        sys.exit(1)
    creds = json.loads(creds_path.read_text())
    r = httpx.post(f"{BASE}/auth/login", json=creds)
    if r.status_code != 200:
        print("login as eval user failed:", r.text); sys.exit(1)
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    per_query = []
    for row in rows:
        r = httpx.post(f"{BASE}/search", headers=headers, json={
            "query": row["query"], "top_k": 10, "use_reranker": True,
        }, timeout=120)
        results = r.json()["results"]
        ranks = []
        for i, hit in enumerate(results, start=1):
            if _is_relevant(hit, row["expected_document_title"], row["expected_chunk_fingerprint"]):
                ranks.append(i)
        per_query.append({
            "query": row["query"],
            "expected": row["expected_document_title"],
            "relevant_ranks": ranks,
            "top_1_title": results[0]["document_title"] if results else None,
        })

    metrics = {}
    for k in KS:
        hits = sum(1 for r in per_query if any(rank <= k for rank in r["relevant_ranks"]))
        metrics[f"Recall@{k}"] = round(hits / len(per_query), 4)

    rr = []
    for r in per_query:
        rr.append(1.0 / r["relevant_ranks"][0] if r["relevant_ranks"] else 0.0)
    metrics["MRR"] = round(sum(rr) / len(rr), 4)

    for k in [5, 10]:
        ndcgs = []
        for r in per_query:
            rels = [1 if rank <= k and rank in r["relevant_ranks"] else 0 for rank in range(1, k + 1)]
            ideal = [1] + [0] * (k - 1)
            dcg = _dcg(rels)
            idcg = _dcg(ideal)
            ndcgs.append(dcg / idcg if idcg > 0 else 0.0)
        metrics[f"nDCG@{k}"] = round(sum(ndcgs) / len(ndcgs), 4)

    print("\n=== Retrieval quality ===")
    for k, v in metrics.items():
        print(f"{k:10s} = {v}")
    OUT.write_text(json.dumps({
        "n_queries": len(per_query),
        "metrics": metrics,
        "per_query": per_query,
    }, indent=2))
    print(f"\nsaved -> {OUT}")


if __name__ == "__main__":
    main()
