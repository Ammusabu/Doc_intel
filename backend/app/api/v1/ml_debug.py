"""
TEMPORARY internal debug endpoints so you can curl each DL model independently
before Phase 3's upload pipeline exists. Remove (or gate behind admin auth) in Phase 3.
"""
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/ml", tags=["ml-debug"])


class ClassifyRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=32)


class EmbedRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=256)


class RerankRequest(BaseModel):
    query: str = Field(..., min_length=1)
    candidates: list[str] = Field(..., min_length=1, max_length=100)
    top_k: int | None = None


@router.post("/classify")
async def ml_classify(body: ClassifyRequest, request: Request):
    clf = request.app.state.classifier
    return {"results": clf.predict(body.texts)}


@router.post("/embed")
async def ml_embed(body: EmbedRequest, request: Request):
    emb = request.app.state.embedder
    vecs = emb.encode(body.texts)
    return {
        "model": emb.model_name,
        "version": emb.model_version,
        "dim": emb.dim,
        "shape": list(vecs.shape),
        "vectors": vecs.tolist(),
    }


@router.post("/rerank")
async def ml_rerank(body: RerankRequest, request: Request):
    rk = request.app.state.reranker
    candidates = [{"content": c} for c in body.candidates]
    ranked = rk.rerank(body.query, candidates, top_k=body.top_k)
    return {
        "model": rk.model_name,
        "version": rk.model_version,
        "results": ranked,
    }
