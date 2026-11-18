"""Document upload, listing, status, detail, chunks, delete endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.chunk import DocumentChunk
from app.models.user import User
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.document_repo import DocumentRepository
from app.schemas.document import (
    DocumentListOut, DocumentOut, DocumentStatusOut, UploadResponse,
)
from app.services.document_service import DocumentService
from app.services.storage import StorageClient

router = APIRouter(prefix="/documents", tags=["documents"])
MAX_FILE_BYTES = 25 * 1024 * 1024


class ChunkOut(BaseModel):
    id: uuid.UUID
    chunk_index: int
    page_number: int
    token_count: int
    content: str
    embedding_model: str
    embedding_version: str
    has_embedding: bool

    model_config = {"from_attributes": False}


class ChunksResponse(BaseModel):
    document_id: uuid.UUID
    total: int
    embedding_model: str | None
    embedding_version: str | None
    chunks: list[ChunkOut]


class TextResponse(BaseModel):
    document_id: uuid.UUID
    page_count: int
    text_by_page: list[dict]


@router.post("", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await file.read()
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(413, f"file too large (max {MAX_FILE_BYTES // (1024*1024)} MB)")
    service = DocumentService(db)
    try:
        doc = await service.create_from_upload(
            owner=current_user, file_bytes=data, filename=file.filename, title=title,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    await service.enqueue(doc.id)
    return UploadResponse(id=doc.id, status=doc.status)


@router.get("", response_model=DocumentListOut)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = DocumentRepository(db)
    items, total = await repo.list_for_owner(
        current_user.id, page=page, page_size=page_size, status=status_filter,
    )
    return DocumentListOut(
        items=[DocumentOut.model_validate(d) for d in items],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = DocumentRepository(db)
    doc = await repo.get_by_id(doc_id, owner_id=current_user.id)
    if not doc:
        raise HTTPException(404, "document not found")
    return doc


@router.get("/{doc_id}/status", response_model=DocumentStatusOut)
async def get_document_status(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = DocumentRepository(db)
    doc = await repo.get_by_id(doc_id, owner_id=current_user.id)
    if not doc:
        raise HTTPException(404, "document not found")
    return DocumentStatusOut(id=doc.id, status=doc.status, error_message=doc.error_message)


@router.get("/{doc_id}/chunks", response_model=ChunksResponse)
async def get_document_chunks(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_by_id(doc_id, owner_id=current_user.id)
    if not doc:
        raise HTTPException(404, "document not found")

    rows = (await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == doc_id)
        .order_by(DocumentChunk.chunk_index)
    )).scalars().all()

    embedding_model = rows[0].embedding_model if rows else None
    embedding_version = rows[0].embedding_version if rows else None

    return ChunksResponse(
        document_id=doc_id,
        total=len(rows),
        embedding_model=embedding_model,
        embedding_version=embedding_version,
        chunks=[
            ChunkOut(
                id=c.id,
                chunk_index=c.chunk_index,
                page_number=c.page_number,
                token_count=c.token_count,
                content=c.content,
                embedding_model=c.embedding_model,
                embedding_version=c.embedding_version,
                has_embedding=c.embedding is not None,
            )
            for c in rows
        ],
    )


@router.get("/{doc_id}/text", response_model=TextResponse)
async def get_document_text(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_by_id(doc_id, owner_id=current_user.id)
    if not doc:
        raise HTTPException(404, "document not found")

    rows = (await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == doc_id)
        .order_by(DocumentChunk.page_number, DocumentChunk.chunk_index)
    )).scalars().all()

    by_page: dict[int, list[str]] = {}
    for c in rows:
        by_page.setdefault(c.page_number, []).append(c.content)

    text_by_page = [
        {"page_number": p, "text": "\n\n".join(by_page[p])}
        for p in sorted(by_page.keys())
    ]
    return TextResponse(
        document_id=doc_id,
        page_count=doc.page_count,
        text_by_page=text_by_page,
    )




from fastapi.responses import StreamingResponse
import io


@router.get("/{doc_id}/download")
async def download_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = DocumentRepository(db)
    doc = await repo.get_by_id(doc_id, owner_id=current_user.id)
    if not doc:
        raise HTTPException(404, "document not found")
    try:
        storage = StorageClient.from_settings()
        data = storage.download(doc.storage_key)
    except Exception as e:
        raise HTTPException(500, f"could not read stored file: {e}")
    return StreamingResponse(
        io.BytesIO(data),
        media_type=doc.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.original_filename}"'},
    )


@router.post("/{doc_id}/reprocess", response_model=DocumentStatusOut)
async def reprocess_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = DocumentRepository(db)
    doc = await repo.get_by_id(doc_id, owner_id=current_user.id)
    if not doc:
        raise HTTPException(404, "document not found")
    await repo.update_status(doc.id, "pending", error_message=None)
    await db.commit()
    service = DocumentService(db)
    await service.enqueue(doc.id)
    return DocumentStatusOut(id=doc.id, status="pending", error_message=None)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = DocumentRepository(db)
    doc = await repo.get_by_id(doc_id, owner_id=current_user.id)
    if not doc:
        raise HTTPException(404, "document not found")
    try:
        StorageClient.from_settings().delete(doc.storage_key)
    except Exception:
        pass
    await repo.delete(doc)
    await db.commit()
