"""App factory. Run with: uv run uvicorn app.main:app --reload"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app import __version__
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import error_response, register_exception_handlers
from app.core.logging import RequestIdMiddleware, configure_logging
from app.core.rate_limit import limiter


async def _rate_limited(request: Request, exc: Exception) -> JSONResponse:
    # All our limits are per minute, so the client can retry after the 60 s window.
    return error_response(
        429,
        "rate_limited",
        "Too many attempts. Please wait and try again.",
        headers={"Retry-After": "60"},
    )


def create_app() -> FastAPI:
    # Fail fast: raises ValidationError here if DATABASE_URL or JWT_SECRET_KEY is missing.
    get_settings()

    app = FastAPI(title="NetDesk API", version=__version__)
    app.add_middleware(RequestIdMiddleware)
    app.state.limiter = limiter
    register_exception_handlers(app)
    app.add_exception_handler(RateLimitExceeded, _rate_limited)
    app.include_router(api_router)
    return app


# Logging is set up once per process, not per create_app(): it replaces the root
# handlers, which would also remove handlers that tests install.
configure_logging()
app = create_app()
