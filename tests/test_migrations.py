"""Alembic builds the schema (never create_all). Needs the database on port 5433."""

import subprocess
from pathlib import Path

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
