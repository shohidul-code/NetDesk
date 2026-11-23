"""MCP over Streamable HTTP at /mcp (PROPOSAL §9.7, §10 MCP access row): staff JWT,
our error envelope for 401/403, host allowlist (421), and one real uvicorn server so the
lifespan that runs the MCP session manager is exercised for real."""

import os
import socket
import subprocess
import sys
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from contextlib import asynccontextmanager

import httpx
import httpx2
import pytest
from fastapi import FastAPI
from mcp.client import Client
from mcp.client.streamable_http import streamable_http_client
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_access_token
from app.main import create_app
from app.mcp import server
from app.modules.users.models import User
from tests.conftest import REPO_ROOT
from tests.factories import make_user

MCP_HEADERS = {"Accept": "application/json, text/event-stream"}
LIST_TOOLS = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}


@pytest.fixture
def mcp_app(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """A fresh app whose MCP mount accepts the test Host and uses the test transaction."""

    @asynccontextmanager
    async def test_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    monkeypatch.setattr(server, "open_session", test_session)
    monkeypatch.setattr(get_settings(), "mcp_allowed_hosts", ["test"])
    return create_app()


async def _post(app: FastAPI, token: str | None, host: str = "test") -> httpx.Response:
    """httpx's ASGITransport does not run lifespans, so start the MCP session manager here
    (inside the test task: anyio forbids entering it in a fixture and leaving elsewhere)."""
    headers = {**MCP_HEADERS, "Host": host}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")
    async with app.router.lifespan_context(app), client:
        return await client.post("/mcp", json=LIST_TOOLS, headers=headers)


async def test_no_token_is_401_in_our_envelope(mcp_app: FastAPI) -> None:
    response = await _post(mcp_app, None)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
    assert response.headers["WWW-Authenticate"] == "Bearer"


async def test_bad_token_is_401(mcp_app: FastAPI) -> None:
    response = await _post(mcp_app, "not-a-jwt")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_customer_token_is_403(mcp_app: FastAPI, db_session: AsyncSession) -> None:
    customer = await make_user(db_session, "customer")

    response = await _post(mcp_app, create_access_token(customer.id)[0])

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


async def test_inactive_staff_is_401(mcp_app: FastAPI, db_session: AsyncSession) -> None:
    technician = await make_user(db_session, "technician", is_active=False)

    response = await _post(mcp_app, create_access_token(technician.id)[0])

    assert response.status_code == 401


async def test_staff_lists_tools(mcp_app: FastAPI, admin: User) -> None:
    response = await _post(mcp_app, create_access_token(admin.id)[0])

    assert response.status_code == 200
    names = {t["name"] for t in response.json()["result"]["tools"]}
    assert names == {"lookup_customer_bills", "get_area_service_status"}


async def test_unknown_host_is_421(mcp_app: FastAPI, admin: User) -> None:
    """DNS-rebinding protection: only hosts in MCP_ALLOWED_HOSTS reach the MCP server."""
    response = await _post(mcp_app, create_access_token(admin.id)[0], host="evil.example")

    assert response.status_code == 421


# --- one real server --------------------------------------------------------------------


@pytest.fixture
def live_server() -> Iterator[str]:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    env = {**os.environ, "MCP_ALLOWED_HOSTS": '["127.0.0.1:*"]'}
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                if httpx.get(f"{base}/api/v1/health", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.2)
        else:
            pytest.fail("uvicorn did not start")
        yield base
    finally:
        proc.terminate()
        proc.wait(timeout=10)


async def test_real_server_sdk_client_lists_and_calls(
    live_server: str, committed_user: Callable[[str], Awaitable[User]]
) -> None:
    token = create_access_token((await committed_user("technician")).id)[0]
    http = httpx2.AsyncClient(headers={"Authorization": f"Bearer {token}"})
    transport = streamable_http_client(f"{live_server}/mcp", http_client=http)

    async with Client(transport) as client:
        tools = {t.name for t in (await client.list_tools()).tools}
        result = await client.call_tool("get_area_service_status", {"area_code": "NO-SUCH-AREA"})
        prompts = {p.name for p in (await client.list_prompts()).prompts}

    assert tools == {"lookup_customer_bills", "get_area_service_status"}
    assert prompts == {"due_bill_reminder"}
    assert result.is_error is True
    assert "Area not found" in result.content[0].text  # type: ignore[union-attr]
