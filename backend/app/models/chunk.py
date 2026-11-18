import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.document import EMBED_DIM


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Dense semantic vector (Model B — all-MiniLM-L6-v2)
    embedding = mapped_column(Vector(EMBED_DIM), nullable=True)
    embedding_model: Mapped[str] = mapped_column(
        String(120), default="all-MiniLM-L6-v2", nullable=False
    )
    embedding_version: Mapped[str] = mapped_column(String(40), default="3.3.1", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        # same document cannot have two chunks with the same index
        Index("uq_chunks_doc_index", "document_id", "chunk_index", unique=True),
        # Full-text GIN index (keyword half of hybrid search)
        Index(
            "ix_chunks_content_fts",
            text("to_tsvector('english', content)"),
            postgresql_using="gin",
        ),
        # pgvector HNSW index for cosine similarity (dense half)
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
