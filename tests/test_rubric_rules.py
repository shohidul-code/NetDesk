"""Quiet rubric slips, caught automatically (PROPOSAL "Refined plan", BUILD_PLAN Phase 1).

Each test guards one rule that is easy to break without noticing.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[1]

# Routes anyone may call without a token (CLAUDE.md). Swagger's own routes are not APIRoutes.
PUBLIC_PATHS = {"/api/v1/health", "/api/v1/auth/register", "/api/v1/auth/login"}

# The auth dependency every other route must use (a stub in Phase 2, real in Phase 3).
AUTH_DEPENDENCY = "get_current_user"


def test_no_create_all_anywhere() -> None:
    """Schema changes go through Alembic only, even in tests."""
    needle = "create_all" + "("  # split so this file does not match itself
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for folder in ("app", "tests", "scripts", "migrations")
        for path in (REPO_ROOT / folder).rglob("*.py")
        if needle in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def _git_tracked(path: str) -> bool:
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", path],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def test_uv_lock_is_tracked_and_env_is_not() -> None:
    assert _git_tracked("uv.lock")
    assert not _git_tracked(".env")


def test_every_setting_is_in_env_example() -> None:
    text = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    documented = set(re.findall(r"^([A-Z][A-Z0-9_]*)=", text, flags=re.MULTILINE))

    missing = {name.upper() for name in Settings.model_fields} - documented

    assert missing == set()


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


def _dependency_names(route: APIRoute) -> set[str]:
    """Names of every dependency a route uses, including nested ones."""
    names: set[str] = set()
    stack = list(route.dependant.dependencies)
    while stack:
        dep = stack.pop()
        if dep.call is not None:
            names.add(getattr(dep.call, "__name__", ""))
        stack.extend(dep.dependencies)
    return names


def test_every_non_public_route_requires_auth() -> None:
    app = create_app()
    unprotected = [
        route.path
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.path not in PUBLIC_PATHS
        and AUTH_DEPENDENCY not in _dependency_names(route)
    ]

    assert unprotected == []


class _Signup(BaseModel):
    email: str
    password: str = Field(min_length=12)


def _app_with_test_routes() -> FastAPI:
    app = create_app()

    @app.post("/test/signup")
    async def signup(body: _Signup) -> dict[str, str]:
        return {"email": body.email}

    @app.get("/test/crash")
    async def crash() -> None:
        raise RuntimeError("secret internal detail")

    return app


async def test_422_body_never_echoes_input() -> None:
    transport = ASGITransport(app=_app_with_test_routes())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/test/signup", json={"email": "a@example.com", "password": "hunter2"}
        )

    assert response.status_code == 422
    assert "input" not in response.text
    assert "hunter2" not in response.text
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"][0]["field"] == "password"


async def test_500_body_has_no_traceback() -> None:
    transport = ASGITransport(app=_app_with_test_routes(), raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/test/crash", headers={"X-Request-ID": "crash-1"})

    assert response.status_code == 500
    # The 500 is sent outside the request-ID middleware, so the handler adds the header itself.
    assert response.headers["X-Request-ID"] == "crash-1"
    assert "Traceback" not in response.text
    assert "secret internal detail" not in response.text
    error = response.json()["error"]
    assert error["code"] == "internal_error"
    assert error["request_id"]
