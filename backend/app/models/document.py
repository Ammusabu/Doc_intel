import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# pgvector dimension for all-MiniLM-L6-v2
EMBED_DIM = 384


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # DL classification results (Phase 2 model fills these)
    predicted_category: Mapped[str | None] = mapped_column(String(50))
    classification_confidence: Mapped[float | None] = mapped_column()

    # Processing lifecycle
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True
    )  # pending | processing | completed | failed
    error_message: Mapped[str | None] = mapped_column(Text)

    # Optional user-provided tags / metadata
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("file_size_bytes > 0", name="ck_documents_size_positive"),
        CheckConstraint(
            "status IN ('pending','processing','completed','failed')",
            name="ck_documents_status_enum",
        ),
        CheckConstraint(
            "classification_confidence IS NULL "
            "OR (classification_confidence >= 0 AND classification_confidence <= 1)",
            name="ck_documents_confidence_range",
        ),
        Index("ix_documents_owner_status", "owner_id", "status"),
        Index("ix_documents_category", "predicted_category"),
    )
