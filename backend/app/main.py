"""
FastAPI entrypoint. Phase 2C: loads all three DL models once at startup.

Startup order:
    1. DocumentClassifier  (fine-tuned DistilBERT)   → app.state.classifier
    2. Embedder            (all-MiniLM-L6-v2)        → app.state.embedder
    3. Reranker            (ms-marco cross-encoder)  → app.state.reranker
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.config import get_settings
from app.ml.classifier import DocumentClassifier
from app.ml.embedder import Embedder
from app.ml.reranker import Reranker

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    t0 = time.time()

    print("[startup] loading DocumentClassifier (fine-tuned DistilBERT)...")
    t = time.time()
    app.state.classifier = DocumentClassifier.load()
    print(f"[startup]   classifier ready in {time.time()-t:.2f}s  device={app.state.classifier.device}")

    print("[startup] loading Embedder (all-MiniLM-L6-v2)...")
    t = time.time()
    app.state.embedder = Embedder.load()
    print(f"[startup]   embedder ready in {time.time()-t:.2f}s  device={app.state.embedder.device}")

    print("[startup] loading Reranker (ms-marco-MiniLM-L-6-v2)...")
    t = time.time()
    app.state.reranker = Reranker.load()
    print(f"[startup]   reranker ready in {time.time()-t:.2f}s  device={app.state.reranker.device}")

    print(f"[startup] all models loaded in {time.time()-t0:.2f}s")
    yield
    print("[shutdown] DocIntel API stopped")


app = FastAPI(
    title="DocIntel — Intelligent Document Management & Retrieval",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
