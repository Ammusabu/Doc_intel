"""
Celery tasks — run inside the worker process (production).

In tests (CELERY_EAGER=1) this task is bypassed: DocumentService.enqueue
calls `_run_ingest` directly inside the current event loop, avoiding the
`asyncio.run() inside a running loop` problem.

In production the worker process has no running loop, so `asyncio.run` is safe.
"""
from __future__ import annotations

import asyncio
import uuid

from worker.celery_app import celery_app

_models: dict = {}


def _load_models() -> None:
    if "classifier" in _models:
        return
    from app.ml.classifier import DocumentClassifier
    from app.ml.embedder import Embedder
    print("[worker] loading DL models (once per worker process)...")
    _models["classifier"] = DocumentClassifier.load()
    _models["embedder"] = Embedder.load()
    print("[worker] models ready")


async def _run_ingest(document_id: str) -> dict:
    """The async ingestion coroutine — used by both eager tests and production worker."""
    from app.db.session import _get_engine_and_factory
    from app.repositories.document_repo import DocumentRepository
    from app.services.ingest import ingest_document
    from app.services.storage import StorageClient

    _load_models()

    _, factory = _get_engine_and_factory()
    async with factory() as db:
        doc_repo = DocumentRepository(db)
        doc = await doc_repo.get_by_id(uuid.UUID(document_id))
        if not doc:
            return {"error": "document not found"}

        storage = StorageClient.from_settings()
        file_bytes = storage.download(doc.storage_key)

        return await ingest_document(
            db,
            document_id=doc.id,
            file_bytes=file_bytes,
            mime_type=doc.mime_type,
            classifier=_models["classifier"],
            embedder=_models["embedder"],
        )


@celery_app.task(name="worker.process_document", bind=True)
def process_document(self, document_id: str) -> dict:
    try:
        return asyncio.run(_run_ingest(document_id))
    except Exception as exc:
        print(f"[worker] ingest failed for {document_id}: {exc}")
        raise
