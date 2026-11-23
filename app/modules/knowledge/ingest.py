"""Pure functions that turn a Markdown file into validated, chunked text (PROPOSAL §9.6).

No database and no network here, so every rule is easy to unit-test.
"""

import hashlib
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

MAX_FILE_BYTES = 50 * 1024
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REQUIRED_KEYS = ("slug", "title", "language", "visibility", "status", "updated")
CHOICES = {
    "language": ("bn", "en"),
    "visibility": ("public", "staff"),
    "status": ("active", "archived"),
}
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
# A sentence ends at . ? ! or the Bangla danda, followed by whitespace; a newline also splits.
SENTENCE_END = re.compile(r"(?<=[.?!।])\s+|\n")


class InvalidDocumentError(Exception):
    """A knowledge file failed validation. Names the file so the admin can fix it."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"{path}: {reason}")
        self.path = path
        self.reason = reason


@dataclass(frozen=True)
class ParsedDocument:
    slug: str
    title: str
    language: str
    visibility: str
    status: str
    updated: date
    body: str
    sha256: str


def parse_document(path: Path) -> ParsedDocument:
    raw = path.read_bytes()
    if len(raw) > MAX_FILE_BYTES:
        raise InvalidDocumentError(path, f"file is {len(raw)} bytes; the limit is 50 KB")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidDocumentError(path, "file is not valid UTF-8") from exc

    fields, body = _split_front_matter(path, text)
    for key in REQUIRED_KEYS:
        if not fields.get(key):
            raise InvalidDocumentError(path, f"front matter is missing '{key}'")

    slug, title = fields["slug"], fields["title"]
    if len(slug) > 120 or not SLUG_PATTERN.match(slug):
        raise InvalidDocumentError(path, "slug must be lowercase words joined by '-', max 120")
    if len(title) > 200:
        raise InvalidDocumentError(path, "title is longer than 200 characters")
    for key, allowed in CHOICES.items():
        if fields[key] not in allowed:
            raise InvalidDocumentError(path, f"{key} must be one of {', '.join(allowed)}")
    if not DATE_PATTERN.match(fields["updated"]):
        raise InvalidDocumentError(path, "updated must look like YYYY-MM-DD")
    try:
        updated = date.fromisoformat(fields["updated"])
    except ValueError as exc:
        raise InvalidDocumentError(path, "updated is not a real date") from exc

    # The body is trusted admin content; stripping tags is defence in depth, not the main control.
    body = re.sub(r"<[^>]+>", "", body)
    if not body.strip():
        raise InvalidDocumentError(path, "body is empty")

    return ParsedDocument(
        slug=slug,
        title=title,
        language=fields["language"],
        visibility=fields["visibility"],
        status=fields["status"],
        updated=updated,
        body=body,
        sha256=hashlib.sha256(raw).hexdigest(),
    )


def _split_front_matter(path: Path, text: str) -> tuple[dict[str, str], str]:
    """Tiny `key: value` reader, so the app needs no YAML dependency."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise InvalidDocumentError(path, "front matter must start with a '---' line")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise InvalidDocumentError(path, "front matter is not closed by a '---' line") from None

    fields: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        if ": " not in line and not line.rstrip().endswith(":"):
            raise InvalidDocumentError(path, f"front matter line is not 'key: value': {line!r}")
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip("\"'").strip()
    return fields, "\n".join(lines[end + 1 :])


def _max_chars(max_tokens: int) -> int:
    # shortcut: character-based token estimate,
    # swap for the model's tokenizer if chunks hit the 512-token limit
    return max_tokens * 3


def _split_long(paragraph: str, max_chars: int) -> list[str]:
    """Break one oversized paragraph into pieces of at most `max_chars`, at sentence ends."""
    pieces: list[str] = []
    current = ""
    for sentence in (s.strip() for s in SENTENCE_END.split(paragraph)):
        while len(sentence) > max_chars:  # no sentence break to use: hard cut
            if current:
                pieces.append(current)
                current = ""
            pieces.append(sentence[:max_chars])
            sentence = sentence[max_chars:]
        if not sentence:
            continue
        if current and len(current) + 1 + len(sentence) > max_chars:
            pieces.append(current)
            current = ""
        current = f"{current} {sentence}" if current else sentence
    if current:
        pieces.append(current)
    return pieces


def _overlap_tail(paragraphs: list[str], overlap: float) -> list[str]:
    """The last paragraphs of a full chunk worth about `overlap` of its size (at least one)."""
    target = overlap * sum(len(p) for p in paragraphs)
    tail: list[str] = []
    size = 0
    for paragraph in reversed(paragraphs[1:]):  # never the whole chunk, so we always progress
        tail.insert(0, paragraph)
        size += len(paragraph)
        if size >= target:
            break
    return tail


def _pack(paragraphs: list[str], max_chars: int, overlap: float) -> list[str]:
    pieces = [piece for p in paragraphs for piece in _split_long(p, max_chars)]
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for piece in pieces:
        if current and size + 2 + len(piece) > max_chars:
            chunks.append("\n\n".join(current))
            current = _overlap_tail(current, overlap)
            size = len("\n\n".join(current))
            if current and size + 2 + len(piece) > max_chars:
                current, size = [], 0  # no room for the overlap next to this piece
        size += len(piece) + (2 if current else 0)
        current.append(piece)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def chunk_markdown(
    title: str, body: str, *, max_tokens: int = 350, overlap: float = 0.15
) -> list[str]:
    """Split on headings, pack paragraphs up to `max_tokens`, prefix each chunk with its path."""
    max_chars = _max_chars(max_tokens)
    sections: list[tuple[list[str], list[str]]] = []  # (heading path, paragraphs)
    path: list[tuple[int, str]] = []
    lines: list[str] = []

    def close_section() -> None:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", "\n".join(lines)) if p.strip()]
        if paragraphs:
            sections.append(([name for _, name in path], paragraphs))
        lines.clear()

    for line in body.splitlines():
        match = HEADING.match(line)
        if not match:
            lines.append(line)
            continue
        close_section()
        level = len(match.group(1))
        while path and path[-1][0] >= level:
            path.pop()
        path.append((level, match.group(2)))
    close_section()

    chunks: list[str] = []
    for headings, paragraphs in sections:
        prefix = " > ".join([title, *headings])
        chunks.extend(f"{prefix}\n\n{text}" for text in _pack(paragraphs, max_chars, overlap))
    return chunks
