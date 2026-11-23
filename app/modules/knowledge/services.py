"""Ingest rules: skip unchanged files, embed first, then replace a document in one transaction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge import repositories
from app.modules.knowledge.ingest import (
    InvalidDocumentError,
    ParsedDocument,
    chunk_markdown,
    parse_document,
)
from app.modules.knowledge.models import EMBEDDING_DIMENSIONS

if TYPE_CHECKING:
    from app.integrations.embeddings import Embedder


class EmbeddingDimensionError(Exception):
    """The embedder returned vectors that do not fit the 384-dimension column."""


@dataclass(frozen=True)
class IngestOutcome:
    slug: str
    action: Literal["created", "updated", "skipped"]
    chunks: int


async def ingest_file(
    session: AsyncSession, embedder: Embedder, path: Path, *, rebuild: bool = False
) -> IngestOutcome:
    return await _ingest(session, embedder, parse_document(path), rebuild)


async def ingest_directory(
    session: AsyncSession, embedder: Embedder, directory: Path, *, rebuild: bool = False
) -> list[IngestOutcome]:
    # Validate every file before writing any, so one bad file fails the run with nothing changed.
    files = {path: parse_document(path) for path in sorted(directory.glob("*.md"))}
    seen: dict[str, Path] = {}
    for path, parsed in files.items():
        if parsed.slug in seen:
            raise InvalidDocumentError(
                path, f"slug '{parsed.slug}' is already used by {seen[parsed.slug].name}"
            )
        seen[parsed.slug] = path
    return [await _ingest(session, embedder, parsed, rebuild) for parsed in files.values()]


async def _ingest(
    session: AsyncSession, embedder: Embedder, parsed: ParsedDocument, rebuild: bool
) -> IngestOutcome:
    existing = await repositories.get_document_by_slug(session, parsed.slug)
    if (
        existing is not None
        and not rebuild
        and existing.content_sha256 == parsed.sha256
        and existing.embedding_model == embedder.model_name
    ):
        chunks = await repositories.count_chunks(session, existing.id)
        return IngestOutcome(parsed.slug, "skipped", chunks)

    contents = chunk_markdown(parsed.title, parsed.body)
    # Embed everything before touching the database: if the model fails, nothing is written.
    vectors = await embedder.embed_passages(contents) if contents else []
    if len(vectors) != len(contents) or any(len(v) != EMBEDDING_DIMENSIONS for v in vectors):
        raise EmbeddingDimensionError(
            f"expected {len(contents)} vectors of {EMBEDDING_DIMENSIONS} floats for {parsed.slug}"
        )

    document = await repositories.save_document(session, existing, parsed, embedder.model_name)
    await repositories.delete_chunks(session, document.id)
    await repositories.insert_chunks(session, document.id, contents, vectors)
    await session.commit()
    return IngestOutcome(parsed.slug, "created" if existing is None else "updated", len(contents))
