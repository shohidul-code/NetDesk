import json
import logging

from httpx import AsyncClient

from app.core.logging import JsonFormatter, request_id_var


async def test_unknown_route_returns_404_envelope(client: AsyncClient) -> None:
    response = await client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert set(error) == {"code", "message", "details", "request_id"}
    assert error["request_id"] == response.headers["X-Request-ID"]


async def test_safe_incoming_request_id_is_kept(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health", headers={"X-Request-ID": "abc-123"})

    assert response.headers["X-Request-ID"] == "abc-123"


async def test_unsafe_incoming_request_id_is_replaced(client: AsyncClient) -> None:
    """A request ID ends up in logs, so one with odd characters could forge log lines."""
    response = await client.get("/api/v1/health", headers={"X-Request-ID": "bad id!injected"})

    assert response.headers["X-Request-ID"] != "bad id!injected"
    assert response.headers["X-Request-ID"].isalnum()


def test_log_lines_are_json_with_request_id() -> None:
    token = request_id_var.set("req-42")
    try:
        record = logging.LogRecord("netdesk", logging.INFO, __file__, 1, "hello", None, None)
        line = json.loads(JsonFormatter().format(record))
    finally:
        request_id_var.reset(token)

    assert line["message"] == "hello"
    assert line["level"] == "INFO"
    assert line["request_id"] == "req-42"
