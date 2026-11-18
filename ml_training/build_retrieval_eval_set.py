"""
Ingest 5 sample documents and write 10 (query, relevant_fingerprint) pairs
used by eval_retrieval.py to compute Recall@K / MRR / nDCG@K.

Fingerprints are the first 40 chars of the ground-truth chunk content — robust
against chunk_id changing between ingest runs (since UUIDs are regenerated).
"""
from __future__ import annotations

import httpx
import json
import os
import sys
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / "backend" / ".env")

BASE = "http://localhost:8000/api/v1"
OUT = Path(__file__).parent / "retrieval_queries.jsonl"

CORPUS = {
    "tech_graphics.txt": (
        "The graphics card supports 1024x768 resolution and 256 colors. "
        "The driver initialization for the X window system failed during boot. "
        "Recompile the kernel module for the new hardware revision to enable proper display output. "
        "The firmware version must match the hardware revision exactly or the OS will hang during boot."
    ),
    "finance_q3.txt": (
        "Quarterly revenue increased 12% year over year to $4.2M. Operating costs declined 3% "
        "following the infrastructure consolidation. The board approved a $500K R&D budget increase. "
        "Cash reserves remained stable at $18M with no new debt issuance."
    ),
    "hr_policy.txt": (
        "All full-time employees receive 20 days of paid time off per calendar year. "
        "Sick leave is separate and accrues at 1 day per month. Remote work is permitted "
        "up to 3 days per week with manager approval. Parental leave is 12 weeks fully paid."
    ),
    "legal_contract.txt": (
        "The agreement shall be governed by the laws of the State of Delaware. "
        "Any disputes shall be resolved through binding arbitration in Wilmington. "
        "Either party may terminate with 30 days written notice. Confidentiality obligations "
        "survive termination for a period of 3 years."
    ),
    "research_ml.txt": (
        "We evaluate transformer models on document classification benchmarks. "
        "DistilBERT achieves 97% of BERT accuracy at 60% of inference cost. "
        "Fine-tuning requires labeled data and careful hyperparameter tuning. "
        "Cross-encoder reranking improves retrieval precision by 8 points over bi-encoders."
    ),
}


def main() -> None:
    email = f"eval_{uuid.uuid4().hex[:8]}@test.com"
    r = httpx.post(f"{BASE}/auth/register", json={
        "email": email, "password": "Passw0rd123", "full_name": "Eval",
    })
    if r.status_code not in (201, 409):
        print("register failed:", r.text); sys.exit(1)
    r = httpx.post(f"{BASE}/auth/login", json={"email": email, "password": "Passw0rd123"})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    for name, text in CORPUS.items():
        files = {"file": (name, text.encode(), "text/plain")}
        r = httpx.post(f"{BASE}/documents", headers=headers, files=files, timeout=120)
        print(f"uploaded {name}: {r.status_code}")

    time.sleep(10)

    queries = [
        ("graphics driver boot failure",              "tech_graphics.txt"),
        ("kernel module hardware revision",           "tech_graphics.txt"),
        ("quarterly revenue growth",                  "finance_q3.txt"),
        ("paid time off policy",                      "hr_policy.txt"),
        ("parental leave duration",                   "hr_policy.txt"),
        ("binding arbitration clause",                "legal_contract.txt"),
        ("Delaware governing law",                    "legal_contract.txt"),
        ("DistilBERT accuracy inference cost",        "research_ml.txt"),
        ("cross-encoder reranking precision",         "research_ml.txt"),
        ("remote work manager approval",              "hr_policy.txt"),
    ]

    rows = []
    for q, doc_name in queries:
        title = doc_name
        r = httpx.post(f"{BASE}/search", headers=headers, json={
            "query": q, "top_k": 3, "use_reranker": False,
        }, timeout=120)
        top = r.json()["results"][0]
        rows.append({
            "query": q,
            "expected_document_title": title,
            "expected_chunk_fingerprint": top["content"][:40],
        })
        print(f"labeled: {q} -> {title}")

    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    creds_path = OUT.parent / "eval_creds.json"
    creds_path.write_text(json.dumps({"email": email, "password": "Passw0rd123"}, indent=2))
    print(f"\nwrote {len(rows)} labeled queries -> {OUT}")
    print(f"wrote credentials -> {creds_path}")


if __name__ == "__main__":
    main()
