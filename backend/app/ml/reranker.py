"""
Cross-encoder wrapper for ms-marco-MiniLM-L-6-v2.

Unlike the bi-encoder (which encodes query and doc separately), the cross-encoder
takes [query, document] as ONE joint input and outputs a single relevance logit.
Slower per pair but far more accurate — so we only run it on the hybrid-search
candidate set (typically 20–50 chunks), never the whole corpus.

Load once at startup (Phase 2C wires into FastAPI lifespan).
"""
from __future__ import annotations

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
MODEL_VERSION = "4.47.1"   # matches transformers==4.47.1 in requirements.txt


def _pick_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


class Reranker:
    def __init__(self, model, tokenizer, device):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.model_name = MODEL_NAME
        self.model_version = MODEL_VERSION

    @classmethod
    def load(cls) -> "Reranker":
        device = _pick_device()
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME).to(device).eval()
        return cls(model, tokenizer, device)

    @torch.no_grad()
    def score(
        self,
        query: str,
        documents: list[str],
        batch_size: int = 32,
    ) -> list[float]:
        """
        Score each (query, doc) pair jointly. Returns one float per document.
        Higher = more relevant. Raw logits — not softmaxed, not 0-1 bounded.
        """
        if not documents:
            return []
        scores: list[float] = []
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            enc = self.tokenizer(
                [query] * len(batch),
                batch,
                truncation=True,
                max_length=512,
                padding=True,
                return_tensors="pt",
            ).to(self.device)
            logits = self.model(**enc).logits.squeeze(-1)
            scores.extend(logits.cpu().tolist())
        return scores

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        text_key: str = "content",
        top_k: int | None = None,
    ) -> list[dict]:
        """
        Rerank `candidates` (list of dicts that contain `text_key`) by relevance to `query`.
        Adds `rerank_score` to each, returns sorted descending.
        """
        if not candidates:
            return []
        texts = [c[text_key] for c in candidates]
        scores = self.score(query, texts)
        enriched = [{**c, "rerank_score": s} for c, s in zip(candidates, scores)]
        enriched.sort(key=lambda x: x["rerank_score"], reverse=True)
        return enriched[:top_k] if top_k else enriched
