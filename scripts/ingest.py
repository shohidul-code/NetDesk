"""Load the knowledge/ articles into the database (PROPOSAL §9.6). Safe to run repeatedly.

    docker compose exec api python -m scripts.ingest [--dir knowledge] [--rebuild]

An unchanged file is skipped. --rebuild re-embeds everything, for example after changing the
embedding model; it first checks that the model returns 384-dimension vectors.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from app.core.db import get_sessionmaker
from app.integrations.embeddings import EmbeddingsUnavailableError, get_embedder
from app.modules.knowledge.ingest import InvalidDocumentError
from app.modules.knowledge.models import EMBEDDING_DIMENSIONS
from app.modules.knowledge.services import EmbeddingDimensionError, ingest_directory


async def run(directory: Path, rebuild: bool) -> None:
    if not directory.is_dir():
        raise SystemExit(f"error: {directory} is not a directory")
    embedder = get_embedder()
    if rebuild:
        probe = await embedder.embed_query("dimension probe")
        if len(probe) != EMBEDDING_DIMENSIONS:
            raise SystemExit(
                f"error: model returned {len(probe)} dimensions, expected {EMBEDDING_DIMENSIONS}"
            )
    async with get_sessionmaker()() as session:
        outcomes = await ingest_directory(session, embedder, directory, rebuild=rebuild)
    for outcome in outcomes:
        print(f"{outcome.action} {outcome.slug} ({outcome.chunks} chunks)")
    counts = {a: sum(o.action == a for o in outcomes) for a in ("created", "updated", "skipped")}
    print("Done:", ", ".join(f"{n} {a}" for a, n in counts.items()))


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest knowledge articles.")
    parser.add_argument("--dir", type=Path, default=Path("knowledge"))
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    try:
        asyncio.run(run(args.dir, args.rebuild))
    except (InvalidDocumentError, EmbeddingsUnavailableError, EmbeddingDimensionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
