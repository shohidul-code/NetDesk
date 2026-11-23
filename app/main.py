"""App factory. Run with: uv run uvicorn app.main:app --reload"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mcp.server.transport_security import TransportSecuritySettings
from slowapi.errors import RateLimitExceeded
from starlette.routing import Route

from app import __version__
from app.api.v1.router import api_router
from app.core.body_limit import BodySizeLimitMiddleware
from app.core.config import get_settings
from app.core.errors import error_response, register_exception_handlers
from app.core.logging import RequestIdMiddleware, configure_logging
from app.core.rate_limit import limiter
from app.integrations.embeddings import EmbeddingsUnavailableError, get_embedder
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


logger = logging.getLogger(__name__)


async def _warm_embedder() -> None:
    """Wake the embedder together with the API (PROPOSAL §12.3.5): on free Render both sleep,
    and the first chat question should not wait for the embedder's cold start. A failure is
    only logged; chat already degrades without articles."""
    try:
        await get_embedder().embed_query("warm up")
    except EmbeddingsUnavailableError:
        logger.warning("embedder warm-up failed; retrieval stays degraded until it answers")


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
        warm_up = asyncio.create_task(_warm_embedder())  # in the background: startup never waits
        async with session_manager.run():
            yield
        warm_up.cancel()

    app = FastAPI(title="NetDesk API", version=__version__, lifespan=lifespan)
    # Innermost of the three, so a 413 still gets a request id and CORS headers.
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(RequestIdMiddleware)
    # Added last, so it is outermost and error responses carry CORS headers too. Bearer
    # tokens, not cookies, so no credentials; never a wildcard (PROPOSAL §10).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["Retry-After", "X-Request-ID"],
    )
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
