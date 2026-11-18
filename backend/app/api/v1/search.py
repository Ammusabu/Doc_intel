"""POST /search — hybrid retrieval + optional cross-encoder reranking."""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.search import SearchRequest, SearchResponse, SearchResult
from app.services.retrieval.dense import dense_search
from app.services.retrieval.hybrid import reciprocal_rank_fusion
from app.services.retrieval.keyword import keyword_search
from app.services.retrieval.rerank import rerank_results

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search(
    body: SearchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    t0 = time.perf_counter()
    embedder = request.app.state.embedder
    reranker = request.app.state.reranker

    dense = await dense_search(
        db,
        embedder=embedder,
        query=body.query,
        owner_id=current_user.id,
        top_k=body.dense_k,
        category=body.category,
        document_id=body.document_id,
    )
    keyword = await keyword_search(
        db,
        query=body.query,
        owner_id=current_user.id,
        top_k=body.keyword_k,
        category=body.category,
        document_id=body.document_id,
    )
    fused = reciprocal_rank_fusion(dense, keyword, k=body.rrf_k)

    if body.use_reranker and fused:
        ranked = rerank_results(reranker, body.query, fused, top_k=body.top_k)
    else:
        ranked = fused[: body.top_k]
        for i, item in enumerate(ranked, start=1):
            item["final_rank"] = i

    latency_ms = int((time.perf_counter() - t0) * 1000)

    return SearchResponse(
        query=body.query,
        latency_ms=latency_ms,
        results=[SearchResult(**r) for r in ranked],
    )
