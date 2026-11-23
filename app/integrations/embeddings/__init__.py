"""Embedding adapters: pick one with EMBEDDINGS_PROVIDER, share it through get_embedder()."""

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.integrations.embeddings.base import MODEL_NAME, Embedder, EmbeddingsUnavailableError
from app.integrations.embeddings.cache import CachedEmbedder
from app.integrations.embeddings.fake import FakeEmbedder
from app.integrations.embeddings.hf_inference import HFInferenceEmbedder
from app.integrations.embeddings.tei import TEIEmbedder

__all__ = [
    "MODEL_NAME",
    "Embedder",
    "EmbeddingsUnavailableError",
    "FakeEmbedder",
    "build_embedder",
    "get_embedder",
]


class _MissingTokenEmbedder:
    """Stands in when hf_inference has no token, so startup works and only retrieval degrades."""

    model_name = MODEL_NAME

    async def embed_query(self, text: str) -> list[float]:
        raise EmbeddingsUnavailableError("HF_TOKEN is not set")

    async def embed_passages(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingsUnavailableError("HF_TOKEN is not set")


def build_embedder(settings: Settings) -> Embedder:
    inner: Embedder
    if settings.embeddings_provider == "tei":
        inner = TEIEmbedder(settings.embeddings_url, model_name=settings.embeddings_model_label)
    elif settings.embeddings_provider == "hf_inference":
        token = settings.hf_token
        inner = HFInferenceEmbedder(token.get_secret_value()) if token else _MissingTokenEmbedder()
    else:
        inner = FakeEmbedder()
    return CachedEmbedder(inner, maxsize=512)


@lru_cache
def get_embedder() -> Embedder:
    """FastAPI dependency; tests override it."""
    return build_embedder(get_settings())
