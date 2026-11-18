"""Document upload, listing, status, delete endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.document_repo import DocumentRepository
from app.schemas.document import (
    DocumentListOut,
    DocumentOut,
    DocumentStatusOut,
    UploadResponse,
)
from app.services.document_service import DocumentService
from app.services.storage import StorageClient

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_FILE_BYTES = 25 * 1024 * 1024  # 25 MB


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
