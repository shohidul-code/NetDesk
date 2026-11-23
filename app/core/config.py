"""Application settings, read from environment variables (and `.env` in development).

Secrets are `SecretStr`, so they never appear in logs, reprs or tracebacks.
`DATABASE_URL` and `JWT_SECRET_KEY` have no default: if either is missing,
building `Settings` raises `ValidationError` and the app refuses to start.
The full list and examples are in PROPOSAL §12.4 and `.env.example`.
"""

from functools import lru_cache
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # env_ignore_empty: `LLM_API_KEY=` (empty) means "not set" (None), not an empty secret.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    # Required secrets: no default, so startup fails without them.
    database_url: SecretStr
    jwt_secret_key: SecretStr

    @field_validator("database_url")
    @classmethod
    def _asyncpg_url(cls, value: SecretStr) -> SecretStr:
        """Accept the URL Neon's dashboard gives: asyncpg needs the +asyncpg driver, takes
        ssl= instead of sslmode=, and rejects channel_binding= (PROPOSAL §12.4)."""
        parts = urlsplit(value.get_secret_value())
        scheme = (
            "postgresql+asyncpg" if parts.scheme in ("postgres", "postgresql") else parts.scheme
        )
        query = [
            ("ssl" if key == "sslmode" else key, val)
            for key, val in parse_qsl(parts.query)
            if key != "channel_binding"
        ]
        return SecretStr(urlunsplit(parts._replace(scheme=scheme, query=urlencode(query))))

    # Auth
    access_token_expire_minutes: int = 30
    cors_origins: list[str] = []

    # LLM (Phase 4). Gemini through its OpenAI-compatible endpoint.
    operator_name: str = "NetDesk Demo ISP"  # the ISP named in the system prompt
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    llm_model: str = "gemini-3.5-flash-lite"
    llm_api_key: SecretStr | None = None

    # Embeddings (Phase 5)
    embeddings_provider: Literal["tei", "hf_inference", "fake"] = "tei"
    embeddings_url: str = "http://embeddings:80"
    # Stored with every vector; retrieval only compares vectors with the same label. Set it to
    # intfloat/multilingual-e5-small-qint8 when EMBEDDINGS_URL points at the int8 embedder.
    embeddings_model_label: str = "intfloat/multilingual-e5-small"
    # Bearer key for the production embedder (public on Render). Local TEI needs none.
    embeddings_api_key: SecretStr | None = None
    hf_token: SecretStr | None = None
    # Cosine distance limit for evidence (1 - similarity). Tuned on the eval set (PROPOSAL §9.6).
    rag_max_distance: float = 0.16  # tuned on the eval set (docs/EVAL_RESULTS.md)

    # Chat limits and kill switch (Phase 4)
    chat_enabled: bool = True
    chat_daily_limit_customer: int = 30
    chat_daily_limit_staff: int = 100
    chat_daily_limit_global: int = 1500

    # MCP (Phase 6)
    mcp_allowed_hosts: list[str] = ["localhost:8000", "127.0.0.1:8000"]
    # Browser origins allowed to call /mcp; a request without Origin is always allowed.
    mcp_allowed_origins: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]
    mcp_stdio_user_email: str = "admin@netdesk.demo"

    # Complaints: false makes complaint creation admin-only (PROPOSAL §4, conflict 1).
    allow_customer_complaints: bool = True

    # Seed script (Phase 2)
    seed_demo_password: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    """Build the settings once and reuse them."""
    return Settings()
