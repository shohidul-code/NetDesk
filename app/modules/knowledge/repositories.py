"""SQL only for knowledge documents and chunks.

Unlike other modules these take no Scope: ingest is an admin/CLI operation, and the
visibility filter for readers belongs to the retrieval query, not to writing.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.ingest import ParsedDocument
from app.modules.knowledge.models import KnowledgeChunk, KnowledgeDocument


async def get_document_by_slug(session: AsyncSession, slug: str) -> KnowledgeDocument | None:
    query = select(KnowledgeDocument).where(KnowledgeDocument.slug == slug)
    return (await session.execute(query)).scalar_one_or_none()


async def save_document(
    session: AsyncSession,
    existing: KnowledgeDocument | None,
    parsed: ParsedDocument,
    embedding_model: str,
) -> KnowledgeDocument:
    """Insert a new row, or update `existing` in place. Flushes so the id is available."""
    document = existing or KnowledgeDocument(slug=parsed.slug)
    document.title = parsed.title
    document.language = parsed.language
    document.visibility = parsed.visibility
    document.status = parsed.status
    document.source_updated = parsed.updated
    document.content_sha256 = parsed.sha256
    document.embedding_model = embedding_model
    session.add(document)
    await session.flush()
    return document


async def delete_chunks(session: AsyncSession, document_id: uuid.UUID) -> None:
    await session.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id))


async def insert_chunks(
    session: AsyncSession,
    document_id: uuid.UUID,
    contents: Sequence[str],
    embeddings: Sequence[Sequence[float]],
) -> None:
    session.add_all(
        KnowledgeChunk(
            document_id=document_id, chunk_index=i, content=content, embedding=list(vector)
        )
        for i, (content, vector) in enumerate(zip(contents, embeddings, strict=True))
    )
    await session.flush()


async def list_documents(session: AsyncSession) -> Sequence[KnowledgeDocument]:
    query = select(KnowledgeDocument).order_by(KnowledgeDocument.slug)
    return (await session.execute(query)).scalars().all()


async def count_chunks(session: AsyncSession, document_id: uuid.UUID) -> int:
    query = select(func.count()).where(KnowledgeChunk.document_id == document_id)
    return int((await session.execute(query)).scalar_one())
