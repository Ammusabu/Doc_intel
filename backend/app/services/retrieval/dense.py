"""Dense vector similarity search via pgvector cosine distance."""
from __future__ import annotations

import uuid

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.ml.embedder import Embedder


async def dense_search(
    db: AsyncSession,
    *,
    embedder: Embedder,
    query: str,
    owner_id: uuid.UUID,
    top_k: int = 30,
    category: str | None = None,
    document_id: uuid.UUID | None = None,
) -> list[dict]:
    """
    Return top_k chunks ordered by ascending cosine distance (i.e. most similar first).
    Each result includes chunk_id, document_id, content, page_number, chunk_index,
    dense_score (1 - distance, range 0..2 but practically 0..1).
    """
    qvec = embedder.encode([query])[0].astype(np.float32).tolist()

    stmt = (
        select(
            DocumentChunk.id,
            DocumentChunk.document_id,
            DocumentChunk.chunk_index,
            DocumentChunk.page_number,
            DocumentChunk.content,
            DocumentChunk.embedding.cosine_distance(qvec).label("distance"),
            Document.title.label("document_title"),
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(Document.owner_id == owner_id)
        .where(Document.status == "completed")
        .where(DocumentChunk.embedding.isnot(None))
    )
    if category:
        stmt = stmt.where(Document.predicted_category == category)
    if document_id:
        stmt = stmt.where(Document.id == document_id)
    stmt = stmt.order_by("distance").limit(top_k)

    rows = (await db.execute(stmt)).all()
    return [
        {
            "chunk_id": r.id,
            "document_id": r.document_id,
            "document_title": r.document_title,
            "chunk_index": r.chunk_index,
            "page_number": r.page_number,
            "content": r.content,
            "dense_score": float(1.0 - r.distance),
        }
        for r in rows
    ]
