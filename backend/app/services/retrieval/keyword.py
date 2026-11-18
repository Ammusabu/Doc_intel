"""Postgres full-text search using ts_rank_cd."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import DocumentChunk
from app.models.document import Document


async def keyword_search(
    db: AsyncSession,
    *,
    query: str,
    owner_id: uuid.UUID,
    top_k: int = 30,
    category: str | None = None,
    document_id: uuid.UUID | None = None,
) -> list[dict]:
    tsquery = func.plainto_tsquery("english", query)
    tsv = func.to_tsvector("english", DocumentChunk.content)
    rank = func.ts_rank_cd(tsv, tsquery).label("rank")

    stmt = (
        select(
            DocumentChunk.id,
            DocumentChunk.document_id,
            DocumentChunk.chunk_index,
            DocumentChunk.page_number,
            DocumentChunk.content,
            rank,
            Document.title.label("document_title"),
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(Document.owner_id == owner_id)
        .where(Document.status == "completed")
        .where(tsv.op("@@")(tsquery))
    )
    if category:
        stmt = stmt.where(Document.predicted_category == category)
    if document_id:
        stmt = stmt.where(Document.id == document_id)
    stmt = stmt.order_by(rank.desc()).limit(top_k)

    rows = (await db.execute(stmt)).all()
    return [
        {
            "chunk_id": r.id,
            "document_id": r.document_id,
            "document_title": r.document_title,
            "chunk_index": r.chunk_index,
            "page_number": r.page_number,
            "content": r.content,
            "keyword_score": float(r.rank),
        }
        for r in rows
    ]
