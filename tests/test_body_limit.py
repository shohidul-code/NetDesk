"""Oversized requests (PROPOSAL §10.2 "Oversized requests" row): bodies over 64 KB get 413
in our error envelope, whether the client declares the size or streams the body."""

from collections.abc import AsyncIterator

from httpx import AsyncClient

from app.core.body_limit import MAX_BODY_BYTES

LIMIT = MAX_BODY_BYTES


async def test_one_megabyte_body_is_413(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/connections",
        content=b"x" * 1_000_000,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
    error = response.json()["error"]
    assert error["code"] == "payload_too_large"
    assert error["request_id"]


async def test_streamed_body_without_length_is_also_413(client: AsyncClient) -> None:
    """A chunked body has no Content-Length, so the limit must count the bytes it reads."""

    async def chunks() -> AsyncIterator[bytes]:
        for _ in range(20):
            yield b"x" * 8192  # 160 KB in total

    response = await client.post(
        "/api/v1/connections", content=chunks(), headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


async def test_mcp_endpoint_is_limited_too(client: AsyncClient) -> None:
    response = await client.post(
        "/mcp", content=b"x" * (LIMIT + 1), headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 413


async def test_a_body_just_under_the_limit_reaches_validation(client: AsyncClient) -> None:
    """Not a 413: the request gets through and fails validation as normal (422)."""
    response = await client.post(
        "/api/v1/connections",
        content=b'{"customer_name": "' + b"x" * (LIMIT - 100) + b'"}',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
