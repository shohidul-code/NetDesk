"""Knowledge ingest: parsing, validation, chunking and the re-indexing rules (PROPOSAL §9.6).

The embedder is a local stub with deterministic vectors, so these tests need no model server.
Test documents use random slugs, so a real article already in the dev database cannot clash.
"""

import hashlib
import math
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge import repositories
from app.modules.knowledge.ingest import (
    InvalidDocumentError,
    chunk_markdown,
    parse_document,
)
from app.modules.knowledge.models import EMBEDDING_DIMENSIONS, KnowledgeChunk
from app.modules.knowledge.services import EmbeddingDimensionError, ingest_directory, ingest_file

FIXTURES = Path(__file__).parent / "fixtures" / "knowledge"
BODY = "# Title\n\nSome text.\n"


class StubDown(Exception):
    """Stands in for EmbeddingsUnavailableError."""


class StubEmbedder:
    model_name = "stub-model"

    def __init__(
        self, *, fail: bool = False, dims: int = EMBEDDING_DIMENSIONS, model: str = "stub-model"
    ) -> None:
        self.fail = fail
        self.dims = dims
        self.model_name = model
        self.passage_calls = 0

    def _vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        raw = [(digest[i % 32] + 1) / 256 for i in range(self.dims)]
        norm = math.sqrt(sum(x * x for x in raw))
        return [x / norm for x in raw]

    async def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    async def embed_passages(self, texts: list[str]) -> list[list[float]]:
        self.passage_calls += 1
        if self.fail:
            raise StubDown("model server is down")
        return [self._vector(t) for t in texts]


def write_doc(
    directory: Path,
    *,
    name: str | None = None,
    body: str = BODY,
    drop: str | None = None,
    **overrides: str,
) -> Path:
    fields = {
        "slug": f"t-{uuid.uuid4().hex[:10]}",
        "title": "A test article",
        "language": "en",
        "visibility": "public",
        "status": "active",
        "updated": "2026-10-01",
    }
    fields.update(overrides)
    if drop:
        del fields[drop]
    head = "\n".join(f"{k}: {v}" for k, v in fields.items())
    path = directory / (name or f"{fields.get('slug', 'doc')}.md")
    path.write_text(f"---\n{head}\n---\n{body}", encoding="utf-8")
    return path


# --- front matter and validation -------------------------------------------------------------


def test_parse_valid_document(tmp_path: Path) -> None:
    path = write_doc(tmp_path, slug="my-doc", title='"Quoted: title"', updated="2026-10-05")
    doc = parse_document(path)

    assert doc.slug == "my-doc"
    assert doc.title == "Quoted: title"  # quotes stripped, only the first ": " splits
    assert (doc.language, doc.visibility, doc.status) == ("en", "public", "active")
    assert doc.updated.isoformat() == "2026-10-05"
    assert "Some text." in doc.body


@pytest.mark.parametrize("key", ["slug", "title", "language", "visibility", "status", "updated"])
def test_missing_key_is_named(tmp_path: Path, key: str) -> None:
    with pytest.raises(InvalidDocumentError) as exc:
        parse_document(write_doc(tmp_path, drop=key, name="x.md"))
    assert key in str(exc.value)
    assert "x.md" in str(exc.value)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("slug", "Bad Slug"),
        ("slug", "-leading-dash"),
        ("slug", "a" * 121),
        ("title", ""),
        ("language", "fr"),
        ("visibility", "private"),
        ("status", "draft"),
        ("updated", "yesterday"),
        ("updated", "2026-13-45"),
    ],
)
def test_invalid_value_is_named(tmp_path: Path, key: str, value: str) -> None:
    with pytest.raises(InvalidDocumentError) as exc:
        parse_document(write_doc(tmp_path, **{key: value}))
    assert key in str(exc.value)


def test_front_matter_must_start_and_close(tmp_path: Path) -> None:
    no_start = tmp_path / "a.md"
    no_start.write_text("# just markdown\n", encoding="utf-8")
    unclosed = tmp_path / "b.md"
    unclosed.write_text("---\nslug: x\n", encoding="utf-8")

    for path in (no_start, unclosed):
        with pytest.raises(InvalidDocumentError, match="front matter"):
            parse_document(path)


def test_empty_body_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(InvalidDocumentError, match="body"):
        parse_document(write_doc(tmp_path, body="\n<!-- only a comment -->\n"))


def test_size_limit_is_50_kb(tmp_path: Path) -> None:
    probe = write_doc(tmp_path, slug="big", body="", name="probe.md")
    padding = 51200 - probe.stat().st_size
    ok = write_doc(tmp_path, slug="big", body="a" * padding, name="ok.md")
    too_big = write_doc(tmp_path, slug="big", body="a" * (padding + 1), name="big.md")

    assert ok.stat().st_size == 51200
    assert parse_document(ok).slug == "big"
    with pytest.raises(InvalidDocumentError, match="50 KB"):
        parse_document(too_big)


def test_non_utf8_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.md"
    path.write_bytes(b"---\nslug: x\n---\n\xff\xfe broken")
    with pytest.raises(InvalidDocumentError, match="UTF-8"):
        parse_document(path)


def test_html_is_stripped(tmp_path: Path) -> None:
    body = "# T\n\nHello <b>bold</b> <script>alert(1)</script>world\n"
    doc = parse_document(write_doc(tmp_path, body=body))

    assert "<" not in doc.body
    assert "Hello bold alert(1)world" in doc.body


def test_sha256_is_of_the_raw_bytes_and_stable(tmp_path: Path) -> None:
    path = write_doc(tmp_path)
    expected = hashlib.sha256(path.read_bytes()).hexdigest()

    assert parse_document(path).sha256 == expected
    assert parse_document(path).sha256 == expected


# --- chunking --------------------------------------------------------------------------------


def test_chunk_prefix_carries_the_heading_path() -> None:
    body = "# A\n\n## B\n\ntext b\n\n## C\n\ntext c\n\n# D\n\ntext d"
    assert chunk_markdown("T", body) == [
        "T > A > B\n\ntext b",
        "T > A > C\n\ntext c",
        "T > D\n\ntext d",
    ]


def test_chunk_without_heading_has_title_only_prefix() -> None:
    assert chunk_markdown("T", "hello\n\nworld") == ["T\n\nhello\n\nworld"]


def test_empty_sections_are_skipped() -> None:
    assert chunk_markdown("T", "# A\n\n## B\n\n") == []
    assert chunk_markdown("T", "  \n\n") == []


def test_long_section_splits_with_one_paragraph_overlap() -> None:
    paragraphs = [f"Paragraph {i} " + "word " * 20 for i in range(10)]
    paragraphs = [p.strip() for p in paragraphs]
    chunks = chunk_markdown("T", "# S\n\n" + "\n\n".join(paragraphs), max_tokens=100)
    prefix = "T > S\n\n"
    bodies = [c.removeprefix(prefix).split("\n\n") for c in chunks]

    assert len(chunks) > 1
    assert all(c.startswith(prefix) for c in chunks)
    for before, after in zip(bodies, bodies[1:], strict=False):
        assert before[-1] == after[0]  # the overlap
    assert {p for body in bodies for p in body} == set(paragraphs)  # nothing lost


def test_bangla_paragraph_splits_on_danda() -> None:
    sentence = "আমাদের অফিস খোলা আছে।"
    chunks = chunk_markdown("টাইটেল", " ".join([sentence] * 12), max_tokens=30)
    bodies = [c.removeprefix("টাইটেল\n\n") for c in chunks]

    assert len(chunks) > 1
    assert all(b.startswith("আমাদের") and b.endswith("।") for b in bodies)


def test_oversized_text_without_sentence_breaks_is_cut() -> None:
    chunks = chunk_markdown("T", "x" * 1000, max_tokens=50)
    assert len(chunks) > 1
    assert all(len(c) <= len("T\n\n") + 150 for c in chunks)


# --- the ingest service ----------------------------------------------------------------------


async def chunk_contents(session: AsyncSession, slug: str) -> list[str]:
    doc = await repositories.get_document_by_slug(session, slug)
    assert doc is not None
    rows = await session.execute(
        select(KnowledgeChunk.content)
        .where(KnowledgeChunk.document_id == doc.id)
        .order_by(KnowledgeChunk.chunk_index)
    )
    return list(rows.scalars())


async def test_ingest_creates_document_and_chunks(db_session: AsyncSession, tmp_path: Path) -> None:
    path = write_doc(tmp_path, body="# A\n\none\n\n# B\n\ntwo\n")
    embedder = StubEmbedder(model="model-x")
    outcome = await ingest_file(db_session, embedder, path)

    doc = await repositories.get_document_by_slug(db_session, outcome.slug)
    assert doc is not None
    assert (outcome.action, outcome.chunks) == ("created", 2)
    assert doc.embedding_model == "model-x"
    assert doc.content_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert await repositories.count_chunks(db_session, doc.id) == 2
    assert (await chunk_contents(db_session, outcome.slug))[0].startswith("A test article > A")


async def test_second_run_is_skipped_without_embedding(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    path = write_doc(tmp_path)
    embedder = StubEmbedder()
    first = await ingest_file(db_session, embedder, path)
    calls = embedder.passage_calls
    second = await ingest_file(db_session, embedder, path)

    assert second.action == "skipped"
    assert second.chunks == first.chunks
    assert embedder.passage_calls == calls


async def test_changed_file_replaces_the_chunks(db_session: AsyncSession, tmp_path: Path) -> None:
    path = write_doc(tmp_path, body="# A\n\nold one\n\n# B\n\nold two\n\n# C\n\nold three\n")
    embedder = StubEmbedder()
    first = await ingest_file(db_session, embedder, path)
    assert first.chunks == 3

    write_doc(tmp_path, slug=first.slug, body="# A\n\nnew only\n")
    second = await ingest_file(db_session, embedder, path)

    contents = await chunk_contents(db_session, first.slug)
    assert (second.action, second.chunks) == ("updated", 1)
    assert len(contents) == 1
    assert "new only" in contents[0]
    assert all("old" not in c for c in contents)


async def test_rebuild_and_model_change_re_embed(db_session: AsyncSession, tmp_path: Path) -> None:
    path = write_doc(tmp_path)
    embedder = StubEmbedder()
    await ingest_file(db_session, embedder, path)

    rebuilt = await ingest_file(db_session, embedder, path, rebuild=True)
    assert (rebuilt.action, embedder.passage_calls) == ("updated", 2)

    other = StubEmbedder(model="model-y")
    switched = await ingest_file(db_session, other, path)
    doc = await repositories.get_document_by_slug(db_session, switched.slug)
    assert switched.action == "updated"
    assert doc is not None
    assert doc.embedding_model == "model-y"


async def test_embedder_failure_writes_nothing(db_session: AsyncSession, tmp_path: Path) -> None:
    path = write_doc(tmp_path)
    slug = parse_document(path).slug

    with pytest.raises(StubDown):
        await ingest_file(db_session, StubEmbedder(fail=True), path)
    assert await repositories.get_document_by_slug(db_session, slug) is None


async def test_embedder_failure_keeps_the_old_version(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    path = write_doc(tmp_path, body="# A\n\nold text\n")
    first = await ingest_file(db_session, StubEmbedder(), path)
    before = await chunk_contents(db_session, first.slug)

    write_doc(tmp_path, slug=first.slug, body="# A\n\nnew text\n")
    with pytest.raises(StubDown):
        await ingest_file(db_session, StubEmbedder(fail=True), path)

    assert await chunk_contents(db_session, first.slug) == before


async def test_wrong_vector_length_is_refused(db_session: AsyncSession, tmp_path: Path) -> None:
    path = write_doc(tmp_path)
    slug = parse_document(path).slug

    with pytest.raises(EmbeddingDimensionError, match="384"):
        await ingest_file(db_session, StubEmbedder(dims=10), path)
    assert await repositories.get_document_by_slug(db_session, slug) is None


async def test_ingest_directory_ingests_every_fixture_in_order(db_session: AsyncSession) -> None:
    outcomes = await ingest_directory(db_session, StubEmbedder(), FIXTURES)

    assert [o.slug for o in outcomes] == [
        "injection-test",
        "office-hours-bn",
        "old-prices-2025",
        "router-restart",
        "staff-escalation",
    ]
    assert all(o.chunks >= 1 for o in outcomes)
    docs = {d.slug: d for d in await repositories.list_documents(db_session)}
    assert docs["old-prices-2025"].status == "archived"
    assert docs["staff-escalation"].visibility == "staff"
    assert docs["office-hours-bn"].language == "bn"


async def test_invalid_file_fails_the_run_and_names_the_file(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    good = write_doc(tmp_path, name="a-good.md")
    write_doc(tmp_path, name="b-bad.md", language="fr")

    with pytest.raises(InvalidDocumentError, match="b-bad.md"):
        await ingest_directory(db_session, StubEmbedder(), tmp_path)
    # Everything is validated before anything is written.
    assert await repositories.get_document_by_slug(db_session, parse_document(good).slug) is None


async def test_duplicate_slug_in_one_directory_fails(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    write_doc(tmp_path, name="one.md", slug="same-slug")
    write_doc(tmp_path, name="two.md", slug="same-slug")

    with pytest.raises(InvalidDocumentError, match="same-slug"):
        await ingest_directory(db_session, StubEmbedder(), tmp_path)
