"""Help articles and their embedded chunks (PROPOSAL §7.2, §9.6).

Every chunk holds a normalized 384-dimension vector from multilingual-e5-small.
Each document records which model embedded it; retrieval refuses to run if the
configured model differs, so vectors from two models are never mixed.
"""

import uuid
from datetime import date, datetime
from typing import Literal, get_args

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.connections.models import _in_list

EMBEDDING_DIMENSIONS = 384

Language = Literal["bn", "en"]
Visibility = Literal["public", "staff"]
DocumentStatus = Literal["active", "archived"]


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        CheckConstraint(_in_list("language", get_args(Language)), name="language_valid"),
        CheckConstraint(_in_list("visibility", get_args(Visibility)), name="visibility_valid"),
        CheckConstraint(_in_list("status", get_args(DocumentStatus)), name="status_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    language: Mapped[str] = mapped_column(String(2))
    visibility: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(10))
    # From the article's front matter: when its content was last reviewed.
    source_updated: Mapped[date] = mapped_column(Date)
    # Ingest skips a file whose hash has not changed.
    content_sha256: Mapped[str] = mapped_column(String(64))
    embedding_model: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "chunk_index", name="uq_knowledge_chunks_document_id_chunk_index"
        ),
        Index("ix_knowledge_chunks_document_id", "document_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="CASCADE")
    )
    chunk_index: Mapped[int]
    # Includes the "title > heading" prefix, so a chunk makes sense on its own.
    content: Mapped[str] = mapped_column(Text)
    # Exact search in P0 (no index); an HNSW index is P1 (PROPOSAL §5).
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
