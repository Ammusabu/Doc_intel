"""Pydantic schemas for document endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    page_count: int
    predicted_category: str | None
    classification_confidence: float | None
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListOut(BaseModel):
    items: list[DocumentOut]
    total: int
    page: int
    page_size: int


class DocumentStatusOut(BaseModel):
    id: uuid.UUID
    status: str
    error_message: str | None


class UploadResponse(BaseModel):
    id: uuid.UUID
    status: str
    message: str = "Document accepted for processing"
