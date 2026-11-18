"""Pydantic schemas for the /search endpoint."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(10, ge=1, le=50)
    category: str | None = None
    document_id: uuid.UUID | None = None
    use_reranker: bool = True
    dense_k: int = Field(30, ge=1, le=100)
    keyword_k: int = Field(30, ge=1, le=100)
    rrf_k: int = Field(60, ge=1, le=200)


class SearchResult(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    page_number: int
    chunk_index: int
    content: str
    dense_score: float | None = None
    keyword_score: float | None = None
    rrf_score: float
    rerank_score: float | None = None
    final_rank: int


class SearchResponse(BaseModel):
    query: str
    latency_ms: int
    results: list[SearchResult]
