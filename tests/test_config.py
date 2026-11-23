"""Settings behaviour. The missing-secret startup crash is in test_rubric_rules.py."""

import os
from pathlib import Path

import pytest

from app.core.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_env_example_loads_as_valid_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Copying .env.example to .env must give a working config (JSON lists parse, empty = None)."""
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)

    settings = Settings(_env_file=REPO_ROOT / ".env.example")  # type: ignore[call-arg]

    assert settings.mcp_allowed_hosts == ["localhost:8000", "127.0.0.1:8000"]
    assert settings.llm_api_key is None


def test_secrets_are_hidden_in_repr() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    text = repr(settings)

    assert os.environ["JWT_SECRET_KEY"] not in text
    assert os.environ["DATABASE_URL"] not in text


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        # Neon's dashboard string, pasted as is (synthetic host and password).
        (
            "postgresql://neon_user:pw@ep-test-123.ap-southeast-1.aws.neon.tech/netdesk"
            "?sslmode=require&channel_binding=require",
            "postgresql+asyncpg://neon_user:pw@ep-test-123.ap-southeast-1.aws.neon.tech/netdesk"
            "?ssl=require",
        ),
        ("postgres://u:p@h/db", "postgresql+asyncpg://u:p@h/db"),
        # Already in asyncpg form, or local: unchanged.
        ("postgresql+asyncpg://u:p@h/db?ssl=require", "postgresql+asyncpg://u:p@h/db?ssl=require"),
        ("postgresql+asyncpg://netdesk:netdesk@localhost:5433/netdesk", None),
    ],
)
def test_database_url_accepts_neons_default_string(given: str, expected: str | None) -> None:
    """asyncpg rejects sslmode= and channel_binding= (PROPOSAL §12.4), so they are translated."""
    settings = Settings(_env_file=None, database_url=given)  # type: ignore[call-arg]

    assert settings.database_url.get_secret_value() == (expected or given)
