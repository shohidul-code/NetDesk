"""Alembic builds the schema (never create_all). Needs the database on port 5433."""

import subprocess
from pathlib import Path

from sqlalchemy import text

from app.core.db import get_engine

REPO_ROOT = Path(__file__).resolve().parents[1]


def _alembic(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["alembic", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_upgrade_head_succeeds() -> None:
    result = _alembic("upgrade", "head")

    assert result.returncode == 0, result.stderr


def test_models_and_migrations_do_not_drift() -> None:
    """`alembic check` fails if a model changed without a migration."""
    _alembic("upgrade", "head")

    result = _alembic("check")

    assert result.returncode == 0, result.stderr
    assert "No new upgrade operations detected" in result.stdout + result.stderr


def test_downgrade_then_upgrade() -> None:
    """Every migration has a working downgrade (PROPOSAL §7.4)."""
    down = _alembic("downgrade", "base")
    up = _alembic("upgrade", "head")

    assert down.returncode == 0, down.stderr
    assert up.returncode == 0, up.stderr


async def test_migration_inserts_the_three_roles() -> None:
    """Roles are data the app cannot run without, so 0001 inserts them, not the seed."""
    _alembic("upgrade", "head")

    async with get_engine().connect() as conn:
        names = (await conn.execute(text("SELECT name FROM roles ORDER BY id"))).scalars().all()

    assert names == ["admin", "technician", "customer"]
