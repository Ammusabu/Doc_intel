"""
Document service — upload orchestration.
Saves bytes to S3, creates DB row with status=pending, then enqueues background processing.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.user import User
from app.repositories.document_repo import DocumentRepository
from app.services.extractor import mime_from_filename
from app.services.storage import StorageClient


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DocumentRepository(db)

    async def create_from_upload(
        self,
        *,
        owner: User,
        file_bytes: bytes,
        filename: str,
        title: str | None = None,
    ) -> Document:
        mime = mime_from_filename(filename)
        if not mime:
            raise ValueError(f"unsupported file extension: {filename}")
        if not file_bytes:
            raise ValueError("empty file")

        storage = StorageClient.from_settings()
        storage.ensure_bucket()

        doc_id = uuid.uuid4()
        storage_key = f"documents/{owner.id}/{doc_id}/{filename}"
        storage.upload_bytes(file_bytes, storage_key, content_type=mime)

        doc = Document(
            id=doc_id,
            owner_id=owner.id,
            title=title or filename,
            original_filename=filename,
            mime_type=mime,
            file_size_bytes=len(file_bytes),
            storage_key=storage_key,
            status="pending",
        )
        await self.repo.create(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def enqueue(self, document_id: uuid.UUID) -> None:
        """
        Dispatch ingestion. In eager mode (tests, CELERY_EAGER=1) we run the
        ingestion coroutine directly so it executes inside the current event loop.
        In normal mode we send a Celery task to Redis for the worker process.
        """
        from worker.celery_app import celery_app
        if celery_app.conf.task_always_eager:
            from worker.tasks import _run_ingest
            await _run_ingest(str(document_id))
        else:
            from worker.tasks import process_document
            process_document.delay(str(document_id))
