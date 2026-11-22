"""App factory. Run with: uv run uvicorn app.main:app --reload"""

from fastapi import FastAPI

from app import __version__
from app.api.v1.router import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    # Fail fast: raises ValidationError here if DATABASE_URL or JWT_SECRET_KEY is missing.
    get_settings()

    app = FastAPI(title="NetDesk API", version=__version__)
    app.include_router(api_router)
    return app


app = create_app()
