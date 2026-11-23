"""A small in-memory LRU for query embeddings (the same question is often asked twice)."""

from collections import OrderedDict

from app.integrations.embeddings.base import Embedder


class CachedEmbedder:
    def __init__(self, inner: Embedder, maxsize: int = 512) -> None:
        self._inner = inner
        self._maxsize = maxsize
        self._cache: OrderedDict[str, list[float]] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self.model_name = inner.model_name

    async def embed_query(self, text: str) -> list[float]:
        if text in self._cache:
            self._cache.move_to_end(text)
            self._hits += 1
            return self._cache[text]
        self._misses += 1
        vector = await self._inner.embed_query(text)  # a failure raises before anything is stored
        self._cache[text] = vector
        if len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)
        return vector

    async def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return await self._inner.embed_passages(texts)  # ingest only: not worth caching

    def cache_info(self) -> tuple[int, int]:
        return self._hits, self._misses
