"""Hugging Face Inference Providers: the same model without running TEI ourselves."""

import httpx

from app.integrations.embeddings.base import (
    MODEL_NAME,
    PASSAGE_PREFIX,
    QUERY_PREFIX,
    post_for_vectors,
)

# URL follows Hugging Face's router docs; verified against the live service in Phase 9.
URL = f"https://router.huggingface.co/hf-inference/models/{MODEL_NAME}/pipeline/feature-extraction"


class HFInferenceEmbedder:
    model_name = MODEL_NAME

    def __init__(
        self,
        token: str,
        *,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._headers = {"Authorization": f"Bearer {token}"}  # never logged
        self._client = http_client or httpx.AsyncClient()
        self._timeout = timeout

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        return await post_for_vectors(
            self._client, URL, texts, timeout=self._timeout, headers=self._headers
        )

    async def embed_query(self, text: str) -> list[float]:
        return (await self._embed([QUERY_PREFIX + text]))[0]

    async def embed_passages(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await self._embed([PASSAGE_PREFIX + t for t in texts])
