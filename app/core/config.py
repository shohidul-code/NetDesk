"""Application settings, read from environment variables (and `.env` in development).

Secrets are `SecretStr`, so they never appear in logs, reprs or tracebacks.
`DATABASE_URL` and `JWT_SECRET_KEY` have no default: if either is missing,
building `Settings` raises `ValidationError` and the app refuses to start.
The full list and examples are in PROPOSAL §12.4 and `.env.example`.
"""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # env_ignore_empty: `LLM_API_KEY=` (empty) means "not set" (None), not an empty secret.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    # Required secrets: no default, so startup fails without them.
    database_url: SecretStr
    jwt_secret_key: SecretStr

    # Auth
    access_token_expire_minutes: int = 30
    cors_origins: list[str] = []

    # LLM (Phase 4). Gemini through its OpenAI-compatible endpoint.
    operator_name: str = "NetDesk Demo ISP"  # the ISP named in the system prompt
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    llm_model: str = "gemini-2.5-flash-lite"
    llm_api_key: SecretStr | None = None

    # Embeddings (Phase 5)
    embeddings_provider: Literal["tei", "hf_inference", "fake"] = "tei"
    embeddings_url: str = "http://embeddings:80"
    hf_token: SecretStr | None = None

    # Chat limits and kill switch (Phase 4)
    chat_enabled: bool = True
    chat_daily_limit_customer: int = 30
    chat_daily_limit_staff: int = 100
    chat_daily_limit_global: int = 1500

    # MCP (Phase 6)
    mcp_allowed_hosts: list[str] = ["localhost:8000", "127.0.0.1:8000"]
    mcp_stdio_user_email: str = "admin@netdesk.demo"

    # Complaints: false makes complaint creation admin-only (PROPOSAL §4, conflict 1).
    allow_customer_complaints: bool = True

    # Seed script (Phase 2)
    seed_demo_password: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    """Build the settings once and reuse them."""
    return Settings()
