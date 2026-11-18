"""Document repository — all DB access for the Document entity."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document


class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, doc: Document) -> Document:
        self.db.add(doc)
        await self.db.flush()
        await self.db.refresh(doc)
        return doc

    async def get_by_id(self, doc_id: uuid.UUID, owner_id: uuid.UUID | None = None) -> Document | None:
        stmt = select(Document).where(Document.id == doc_id)
        if owner_id is not None:
            stmt = stmt.where(Document.owner_id == owner_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_owner(
        self,
        owner_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[Document], int]:
        stmt = select(Document).where(Document.owner_id == owner_id)
        count_stmt = select(func.count(Document.id)).where(Document.owner_id == owner_id)
        if status:
            stmt = stmt.where(Document.status == status)
            count_stmt = count_stmt.where(Document.status == status)
        stmt = stmt.order_by(Document.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.execute(stmt)).scalars().all()
        total = (await self.db.execute(count_stmt)).scalar_one()
        return list(rows), total

    async def update_status(
        self,
        doc_id: uuid.UUID,
        status: str,
        *,
        error_message: str | None = None,
        predicted_category: str | None = None,
        classification_confidence: float | None = None,
        page_count: int | None = None,
    ) -> None:
        doc = await self.get_by_id(doc_id)
        if not doc:
            return
        doc.status = status
        if error_message is not None:
            doc.error_message = error_message
        if predicted_category is not None:
            doc.predicted_category = predicted_category
        if classification_confidence is not None:
            doc.classification_confidence = classification_confidence
        if page_count is not None:
            doc.page_count = page_count
        await self.db.flush()

    async def delete(self, doc: Document) -> None:
        await self.db.delete(doc)
        await self.db.flush()
