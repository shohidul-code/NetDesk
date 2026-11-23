"""Text Embeddings Inference (Hugging Face's embedding server) running multilingual-e5-small."""

import httpx

from app.integrations.embeddings.base import (
    MODEL_NAME,
    PASSAGE_PREFIX,
    QUERY_PREFIX,
    post_for_vectors,
)


class TEIEmbedder:
    model_name = MODEL_NAME

    def __init__(
        self,
        base_url: str,
        *,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
        batch_size: int = 32,
    ) -> None:
        self._url = base_url.rstrip("/") + "/embed"
        self._client = http_client or httpx.AsyncClient()
        self._timeout = timeout
        self._batch_size = batch_size

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        return await post_for_vectors(self._client, self._url, texts, timeout=self._timeout)

    async def embed_query(self, text: str) -> list[float]:
        return (await self._embed([QUERY_PREFIX + text]))[0]

    async def embed_passages(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = [PASSAGE_PREFIX + t for t in texts[start : start + self._batch_size]]
            vectors.extend(await self._embed(batch))
        return vectors
