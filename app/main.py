"""App factory. Run with: uv run uvicorn app.main:app --reload"""

from fastapi import FastAPI

from app import __version__
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import RequestIdMiddleware, configure_logging


def create_app() -> FastAPI:
    # Fail fast: raises ValidationError here if DATABASE_URL or JWT_SECRET_KEY is missing.
    get_settings()

    app = FastAPI(title="NetDesk API", version=__version__)
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(api_router)
    return app


# Logging is set up once per process, not per create_app(): it replaces the root
# handlers, which would also remove handlers that tests install.
configure_logging()
app = create_app()
