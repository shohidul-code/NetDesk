"""Request body limit (PROPOSAL §10.2 "Oversized requests"): 64 KB, then 413.

The biggest legitimate body is a chat message (1,000 characters) or a notice, far under
64 KB, so anything larger is a mistake or an attack on memory. Two checks:
- a declared Content-Length over the limit is refused before the app runs;
- a streamed body (no Content-Length) is counted as the app reads it. Reading past the
  limit raises, and because FastAPI turns any error while reading a body into its own 400,
  the response the app then starts is replaced with our 413.
"""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import AppError, error_response

MAX_BODY_BYTES = 64 * 1024


class PayloadTooLargeError(AppError):
    status_code = 413
    code = "payload_too_large"


def _too_large() -> PayloadTooLargeError:
    return PayloadTooLargeError(f"The request body is larger than {MAX_BODY_BYTES // 1024} KB.")


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.max_bytes:
            exc = _too_large()
            await error_response(exc.status_code, exc.code, exc.message)(scope, receive, send)
            return

        received = 0
        exceeded = False

        async def limited_receive() -> Message:
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    exceeded = True
                    raise _too_large()
            return message

        async def guarded_send(message: Message) -> None:
            if not exceeded:
                await send(message)
            elif message["type"] == "http.response.start":
                exc = _too_large()
                await error_response(exc.status_code, exc.code, exc.message)(scope, receive, send)
            # else: the rest of the app's own error response is dropped

        await self.app(scope, limited_receive, guarded_send)
