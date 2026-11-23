"""One error envelope for every error (PROPOSAL §8.3):

    {"error": {"code", "message", "details", "request_id"}}

Services raise `AppError` (or a subclass added later); these handlers turn it, and
FastAPI's own errors, into the envelope. A 422 never echoes the submitted value, and
a 500 never shows a traceback.
"""

import logging
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import REQUEST_ID_HEADER, request_id_var

logger = logging.getLogger(__name__)

_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    429: "rate_limited",
    503: "service_unavailable",
}


class AppError(Exception):
    """A business error with a status code and a stable, machine-readable code."""

    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, *, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    request_id = request_id_var.get()
    body = {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id,
        }
    }
    headers = dict(headers or {})
    if request_id:
        # A 500 is sent outside RequestIdMiddleware, so set the header here too.
        headers[REQUEST_ID_HEADER] = request_id
    return JSONResponse(status_code=status_code, content=body, headers=headers)


async def _app_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return error_response(exc.status_code, exc.code, exc.message, exc.details)


async def _http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code = _CODES.get(exc.status_code, "http_error")
    message = exc.detail if isinstance(exc.detail, str) else HTTPStatus(exc.status_code).phrase
    # Keep headers such as Allow (405), WWW-Authenticate (401) and Retry-After (429).
    return error_response(exc.status_code, code, message, headers=exc.headers)


async def _validation_error(request: Request, exc: Exception) -> JSONResponse:
    """FastAPI's default 422 includes `input`, which can hold a password. Keep only
    the field path and the message."""
    assert isinstance(exc, RequestValidationError)
    details = [
        {
            # loc starts with where the value came from ("body", "query"...); drop it.
            "field": ".".join(str(part) for part in err["loc"][1:]) or str(err["loc"][0]),
            "message": err["msg"],
        }
        for err in exc.errors()
    ]
    return error_response(422, "validation_error", "Some fields are invalid.", details)


async def _unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return error_response(
        500,
        "internal_error",
        "Something went wrong. Quote the request ID if you contact support.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(Exception, _unexpected_error)
