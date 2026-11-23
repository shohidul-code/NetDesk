"""JSON logging and the request-ID middleware.

Every request gets an ID. It is returned in the `X-Request-ID` header, put in every
error body, and added to every log line, so one ID ties a user's error report to
the server logs.
"""

import json
import logging
import re
import sys
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime

from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"

# Only short IDs with safe characters are reused; anything else could forge log lines.
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9-]{1,64}$")

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# Redaction (PROPOSAL §10.2 "Sensitive logs"). Order matters: query values first, so
# "q=%2B8801..." is removed whole before the phone pattern runs.
_SECRET_PARAMS = re.compile(r"(?i)\b(password|q|token|access_token)=[^&\s\"']*")
_BEARER = re.compile(r"(?i)\b(bearer\s+)\S+")
_JWT = re.compile(r"\beyJ[\w-]+\.[\w-]+\.[\w-]+")
# Bangladeshi mobiles: 01[3-9] + 8 digits, optionally with 88 / +88 / %2B88 in front.
_PHONE = re.compile(r"(?<![\w])(?:(?:\+|%2B)?88)?01[3-9]\d{8}(?!\d)")


def redact(text: str) -> str:
    """Remove passwords, tokens and search text, and mask phone numbers, in a log line."""
    text = _SECRET_PARAMS.sub(r"\1=[redacted]", text)
    text = _BEARER.sub(r"\1[token]", text)
    text = _JWT.sub("[token]", text)
    return _PHONE.sub("[phone]", text)


class JsonFormatter(logging.Formatter):
    """One JSON object per line, easy to search in Render's log viewer."""

    def format(self, record: logging.LogRecord) -> str:
        line = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
            "request_id": request_id_var.get(),
        }
        if record.exc_info:
            # Tracebacks go to the logs only, never to the client.
            line["exception"] = redact(self.formatException(record.exc_info))
        return json.dumps(line, ensure_ascii=False)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
    # uvicorn installs its own plain-text handlers; send its lines (the access log prints
    # full URLs) through this JSON handler, so they are redacted too.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True


class RequestIdMiddleware:
    """Pure ASGI middleware (not BaseHTTPMiddleware), so the ID set here stays
    visible to the error handlers that run outside it in the same task."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # ASGI header values are latin-1 bytes; utf-8 could raise on odd bytes.
        raw = dict(scope["headers"]).get(REQUEST_ID_HEADER.lower().encode(), b"")
        incoming = raw.decode("latin-1")
        request_id = incoming if _SAFE_REQUEST_ID.match(incoming) else uuid.uuid4().hex[:12]
        request_id_var.set(request_id)

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                # Error responses already carry the header (see errors.error_response).
                if not any(name.lower() == b"x-request-id" for name, _ in headers):
                    headers.append((REQUEST_ID_HEADER.encode(), request_id.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_id)
