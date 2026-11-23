"""Retrieval for one chat turn (PROPOSAL §9.6).

Embed the question, take the nearest active chunks the caller may read (top 4 within
RAG_MAX_DISTANCE), merge neighbouring chunks of one document, and label them [S1]..[S4].
After the model answers, only citations that point at evidence we actually sent become
sources. If the embedder is down, chat still works without articles (graceful failure).
"""

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.integrations.embeddings import Embedder, EmbeddingsUnavailableError
from app.modules.auth.dependencies import Scope
from app.modules.knowledge import repositories

TOP_K = 4
MAX_EVIDENCE_CHARS = 4200  # about 1,400 tokens at ~3 characters per token

# Last outcome of an embedding call, shown on /health. In memory, per process.
embeddings_status: dict[str, str] = {"status": "ok"}


@dataclass(frozen=True)
class Evidence:
    ref: str
    slug: str
    title: str
    language: str
    updated: str
    content: str


@dataclass(frozen=True)
class Citation:
    ref: str
    document_slug: str
    title: str


@dataclass
class Retrieval:
    status: Literal["ok", "no_evidence", "unavailable"]
    evidence: list[Evidence] = field(default_factory=list)


async def retrieve(session: AsyncSession, scope: Scope, embedder: Embedder, text: str) -> Retrieval:
    try:
        vector = await embedder.embed_query(text)
    except EmbeddingsUnavailableError:
        embeddings_status["status"] = "degraded"
        return Retrieval("unavailable")  # reason knowledge_unavailable: answer without articles
    embeddings_status["status"] = "ok"

    rows = await repositories.search_chunks(
        session,
        scope,
        vector,
        model=embedder.model_name,
        max_distance=get_settings().rag_max_distance,
        limit=TOP_K,
    )
    if not rows:
        return Retrieval("no_evidence")

    # Merge chunks of the same document that sit next to each other, keeping rank order.
    groups: list[list[Any]] = []
    for row in rows:
        for group in groups:
            same_doc = group[0].document_id == row.document_id
            if same_doc and any(abs(r.chunk_index - row.chunk_index) == 1 for r in group):
                group.append(row)
                break
        else:
            groups.append([row])

    evidence: list[Evidence] = []
    used = 0
    for group in groups:
        group.sort(key=lambda r: r.chunk_index)
        content = "\n".join(r.content for r in group)
        if evidence and used + len(content) > MAX_EVIDENCE_CHARS:
            break
        used += len(content)
        first = group[0]
        evidence.append(
            Evidence(
                ref=f"S{len(evidence) + 1}",
                slug=first.slug,
                title=first.title,
                language=first.language,
                updated=first.source_updated.isoformat(),
                content=content,
            )
        )
    return Retrieval("ok", evidence)


def format_evidence(evidence: list[Evidence]) -> list[str]:
    """One labelled block per item, in the format prompt v1 expects (PROPOSAL §9.3)."""
    return [
        f"[{e.ref}] (doc: {e.slug}, {e.language}, updated {e.updated}) {e.title}\n{e.content}"
        for e in evidence
    ]


def cited_sources(answer: str, evidence: list[Evidence]) -> list[Citation]:
    """Keep only [S#] references that exist in the evidence we sent, each once, in order."""
    sent = {e.ref: e for e in evidence}
    sources: list[Citation] = []
    for ref in dict.fromkeys(re.findall(r"\[(S\d+)\]", answer)):
        if ref in sent:
            sources.append(Citation(ref, sent[ref].slug, sent[ref].title))
    return sources
