"""Sensitive logs (PROPOSAL §10.2 "Sensitive logs" row): no passwords, tokens or search
text in log lines, phone numbers masked, and uvicorn's access log goes through the same
JSON formatter (it prints full URLs, and search queries can hold a phone number)."""

import logging

import pytest
from httpx import AsyncClient

import app.main  # noqa: F401  (configures logging, as uvicorn's import does)
from app.core.logging import JsonFormatter, redact

JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.c2lnbmF0dXJlLXZhbHVl"


@pytest.mark.parametrize(
    "raw",
    [
        "customer phone +8801712345678",
        "customer phone 8801712345678",
        "customer phone 01712345678",
        '"GET /api/v1/connections?q=%2B8801712345678 HTTP/1.1" 200',
    ],
)
def test_bangladeshi_phone_numbers_are_masked(raw: str) -> None:
    out = redact(raw)

    assert "1712345678" not in out
    assert "[phone]" in out or "q=[redacted]" in out


def test_tokens_passwords_and_search_text_are_removed() -> None:
    line = (
        f"Authorization: Bearer {JWT} body password=hunter2-secret&username=a "
        "GET /x?q=Shirin+Akter&limit=20"
    )

    out = redact(line)

    assert JWT not in out and "hunter2-secret" not in out and "Shirin" not in out
    assert "limit=20" in out  # harmless parameters stay readable


def test_ordinary_numbers_are_left_alone() -> None:
    assert redact("generated 29 bills for 2026-12, amount 1500.00") == (
        "generated 29 bills for 2026-12, amount 1500.00"
    )


async def test_a_login_request_never_logs_the_password(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    secret = "Very-Secret-Pass-2026"
    with caplog.at_level(logging.DEBUG):
        await client.post(
            "/api/v1/auth/login", data={"username": "nobody@netdesk.test", "password": secret}
        )

    lines = [JsonFormatter().format(r) for r in caplog.records]
    assert lines, "expected some log lines from the request"
    assert all(secret not in line for line in lines)


def test_uvicorn_loggers_use_the_json_handler() -> None:
    """configure_logging() already ran when app.main was imported (as under uvicorn); calling
    it again here would replace pytest's own log handlers."""
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        assert logger.handlers == [] and logger.propagate, name
