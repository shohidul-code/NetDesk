"""An offline embedder for tests and demos: hashed bag-of-words, no model, no network."""

import hashlib
import re

from app.integrations.embeddings.base import (
    DIMENSIONS,
    PASSAGE_PREFIX,
    QUERY_PREFIX,
    l2_normalize,
)

# \w is Unicode-aware in Python 3, but Bangla vowel signs are combining marks (\W for `re`),
# so keep marks together with their letters.
_TOKEN = re.compile(r"[\wঀ-৿]+")


class FakeEmbedder:
    # Different from the real model name on purpose: fake and real vectors must never be mixed.
    model_name = "fake-e5-384"

    def _vector(self, text: str) -> list[float]:
        for prefix in (QUERY_PREFIX, PASSAGE_PREFIX):
            text = text.removeprefix(prefix)
        vector = [0.0] * DIMENSIONS
        for token in _TOKEN.findall(text.lower()):
            digest = hashlib.sha256(token.encode()).digest()
            bucket = int.from_bytes(digest[:4], "big") % DIMENSIONS
            vector[bucket] += 1.0 if digest[4] % 2 == 0 else -1.0
        if not any(vector):  # empty text, or tokens that cancelled out: a fixed unit vector
            vector[0] = 1.0
        return l2_normalize(vector)

    async def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    async def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]
