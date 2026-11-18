"""Chunk repository — bulk insert of document chunks with embeddings."""
from __future__ import annotations

import uuid

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import DocumentChunk


class ChunkRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def bulk_insert(
        self,
        document_id: uuid.UUID,
        chunks: list[dict],
        embeddings: np.ndarray,
        embedding_model: str,
        embedding_version: str,
    ) -> int:
        assert len(chunks) == len(embeddings), "chunks and embeddings length mismatch"
        rows = [
            DocumentChunk(
                document_id=document_id,
                chunk_index=c["chunk_index"],
                page_number=c["page_number"],
                content=c["content"],
                token_count=c["token_count"],
                embedding=embeddings[i].tolist(),
                embedding_model=embedding_model,
                embedding_version=embedding_version,
            )
            for i, c in enumerate(chunks)
        ]
        self.db.add_all(rows)
        await self.db.flush()
        return len(rows)

    async def delete_for_document(self, document_id: uuid.UUID) -> None:
        await self.db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))

    async def list_for_document(self, document_id: uuid.UUID) -> list[DocumentChunk]:
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def count_for_document(self, document_id: uuid.UUID) -> int:
        from sqlalchemy import func
        stmt = select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == document_id)
        return (await self.db.execute(stmt)).scalar_one()
