"""
Ingestion pipeline — runs INSIDE the Celery worker.

Given a document ID and its raw bytes:
    1. extract text with page metadata
    2. chunk with the token-aware chunker
    3. classify using the FULL document text (first ~6 chunks ≈ 1,500 tokens)
    4. embed all chunks with all-MiniLM-L6-v2
    5. insert chunks (with embeddings) into Postgres
    6. update document status=completed + predicted_category + confidence

Models are passed in — the caller (Celery task) loads them once per worker process.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.classifier import DocumentClassifier
from app.ml.embedder import Embedder
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.document_repo import DocumentRepository
from app.services.chunker import chunk_document
from app.services.extractor import extract


async def ingest_document(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
    file_bytes: bytes,
    mime_type: str,
    classifier: DocumentClassifier,
    embedder: Embedder,
    chunk_size: int = 256,
    overlap: int = 50,
) -> dict:
    doc_repo = DocumentRepository(db)
    chunk_repo = ChunkRepository(db)

    await doc_repo.update_status(document_id, "processing")
    await db.commit()

    try:
        pages = extract(file_bytes, mime_type)
        if not pages:
            raise ValueError("no extractable text found in document")

        page_texts = [text for _, text in pages]
        chunked = chunk_document(page_texts, chunk_size=chunk_size, overlap=overlap)
        if not chunked:
            raise ValueError("chunking produced no chunks")

        # --- classification on FULL document text (fixes distribution shift) ---
        full_text = " ".join(c["content"] for c in chunked[:6])[:6000]
        cls_result = classifier.predict([full_text])[0]

        # --- embed all chunks in one batch ---
        chunk_texts = [c["content"] for c in chunked]
        embeddings = embedder.encode(chunk_texts)

        # --- clear any prior chunks, insert fresh ---
        await chunk_repo.delete_for_document(document_id)
        inserted = await chunk_repo.bulk_insert(
            document_id=document_id,
            chunks=chunked,
            embeddings=embeddings,
            embedding_model=embedder.model_name,
            embedding_version=embedder.model_version,
        )

        await doc_repo.update_status(
            document_id,
            "completed",
            predicted_category=cls_result["label"],
            classification_confidence=cls_result["confidence"],
            page_count=len(pages),
        )
        await db.commit()

        return {
            "document_id": str(document_id),
            "chunks": inserted,
            "pages": len(pages),
            "category": cls_result["label"],
            "confidence": cls_result["confidence"],
        }

    except Exception as e:
        await db.rollback()
        await doc_repo.update_status(document_id, "failed", error_message=str(e)[:500])
        await db.commit()
        raise
