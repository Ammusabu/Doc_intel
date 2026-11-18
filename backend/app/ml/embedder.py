"""
Bi-encoder wrapper for all-MiniLM-L6-v2.

Produces 384-dim L2-normalized embeddings — so cosine similarity == dot product,
and pgvector's cosine distance operator gives identical ranking to a full re-rank.

Load ONCE at startup (Phase 2C wires this into FastAPI lifespan).
"""
from __future__ import annotations

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
MODEL_VERSION = "3.3.1"   # matches sentence-transformers==3.3.1 in requirements.txt
EMBED_DIM = 384


def _pick_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


class Embedder:
    def __init__(self, model: SentenceTransformer, device: str):
        self.model = model
        self.device = device
        self.model_name = MODEL_NAME
        self.model_version = MODEL_VERSION
        self.dim = EMBED_DIM

    @classmethod
    def load(cls) -> "Embedder":
        device = _pick_device()
        model = SentenceTransformer(MODEL_NAME, device=device)
        model.eval()
        return cls(model, device)

    def encode(self, texts: list[str] | str, batch_size: int = 64) -> np.ndarray:
        """
        Encode one or many texts → np.ndarray[float32] of shape (N, 384), L2-normalized.
        """
        if isinstance(texts, str):
            texts = [texts]
        if not texts:
            return np.zeros((0, EMBED_DIM), dtype=np.float32)
        vecs = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,   # gives us L2-normalized rows
            show_progress_bar=False,
        )
        return vecs.astype(np.float32)
