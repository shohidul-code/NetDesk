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


class JsonFormatter(logging.Formatter):
    """One JSON object per line, easy to search in Render's log viewer."""

    def format(self, record: logging.LogRecord) -> str:
        line = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        if record.exc_info:
            # Tracebacks go to the logs only, never to the client.
            line["exception"] = self.formatException(record.exc_info)
        return json.dumps(line, ensure_ascii=False)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)


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
