"""App factory. Run with: uv run uvicorn app.main:app --reload"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp.server.transport_security import TransportSecuritySettings
from slowapi.errors import RateLimitExceeded
from starlette.routing import Route

from app import __version__
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import error_response, register_exception_handlers
from app.core.logging import RequestIdMiddleware, configure_logging
from app.core.rate_limit import limiter
from app.mcp import server as mcp_server
from app.mcp.auth import StaffJWTMiddleware


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
    settings = get_settings()

    # Stateless: every request gets its own transport, so the tools run inside the
    # request that the JWT middleware checked. Host and Origin come from env (421 / 403).
    mcp_asgi = mcp_server.mcp.streamable_http_app(
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(
            allowed_hosts=settings.mcp_allowed_hosts,
            allowed_origins=settings.mcp_allowed_origins,
        ),
    )
    session_manager = mcp_server.mcp.session_manager  # the one built just above

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # A mounted sub-app's own lifespan never runs, so start the MCP manager here.
        async with session_manager.run():
            yield

    app = FastAPI(title="NetDesk API", version=__version__, lifespan=lifespan)
    app.add_middleware(RequestIdMiddleware)
    app.state.limiter = limiter
    register_exception_handlers(app)
    app.add_exception_handler(RateLimitExceeded, _rate_limited)
    app.include_router(api_router)
    # An exact /mcp route (not a mount), so unknown paths still get our 404 envelope.
    app.router.routes.append(Route("/mcp", endpoint=StaffJWTMiddleware(mcp_asgi)))
    return app


# Logging is set up once per process, not per create_app(): it replaces the root
# handlers, which would also remove handlers that tests install.
configure_logging()
app = create_app()
