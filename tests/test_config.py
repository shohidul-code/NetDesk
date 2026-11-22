import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.core.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("missing", ["DATABASE_URL", "JWT_SECRET_KEY"])
def test_startup_fails_without_required_secret(missing: str, tmp_path: Path) -> None:
    """Import the app in a fresh process, as uvicorn would, with one secret removed.

    The process runs in an empty temp folder so a developer's `.env` cannot fill the gap.
    """
    env = {k: v for k, v in os.environ.items() if k != missing}
    env["PYTHONPATH"] = str(REPO_ROOT)

    result = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "ValidationError" in result.stderr
    assert missing.lower() in result.stderr.lower()


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
