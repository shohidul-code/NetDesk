"""CORS (PROPOSAL §10 "CORS abuse" row): only origins in CORS_ORIGINS get CORS headers,
and the UI can read Retry-After and X-Request-ID from responses."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import create_app

ALLOWED = "http://localhost:5173"


@pytest.fixture
async def cors_client(monkeypatch: pytest.MonkeyPatch) -> AsyncClient:
    monkeypatch.setattr(get_settings(), "cors_origins", [ALLOWED])
    return AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test")


async def test_allowed_origin_gets_cors_headers(cors_client: AsyncClient) -> None:
    async with cors_client as c:
        response = await c.get("/api/v1/health", headers={"Origin": ALLOWED})

    assert response.headers["access-control-allow-origin"] == ALLOWED
    exposed = response.headers["access-control-expose-headers"].lower()
    assert "retry-after" in exposed and "x-request-id" in exposed


async def test_preflight_allows_the_auth_header(cors_client: AsyncClient) -> None:
    async with cors_client as c:
        response = await c.options(
            "/api/v1/connections",
            headers={
                "Origin": ALLOWED,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED
    assert "authorization" in response.headers["access-control-allow-headers"].lower()


async def test_unknown_origin_gets_no_cors_headers(cors_client: AsyncClient) -> None:
    async with cors_client as c:
        response = await c.get("/api/v1/health", headers={"Origin": "https://evil.example"})

    assert "access-control-allow-origin" not in response.headers
