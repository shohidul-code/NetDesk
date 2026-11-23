"""The embeddings contract and the code the real adapters share."""

import math
from typing import Protocol

import httpx

MODEL_NAME = "intfloat/multilingual-e5-small"
DIMENSIONS = 384  # same number as the pgvector column (knowledge.models.EMBEDDING_DIMENSIONS)
QUERY_PREFIX = "query: "  # E5 models need these prefixes; skipping them hurts retrieval quality
PASSAGE_PREFIX = "passage: "


class EmbeddingsUnavailableError(Exception):
    """Vectors could not be produced (network, timeout, HTTP error, bad body, wrong size).

    Retrieval catches this and degrades gracefully instead of failing the request.
    """


class Embedder(Protocol):
    model_name: str

    async def embed_query(self, text: str) -> list[float]: ...

    async def embed_passages(self, texts: list[str]) -> list[list[float]]: ...


def l2_normalize(vector: list[float]) -> list[float]:
    length = math.sqrt(sum(x * x for x in vector))
    if length == 0:
        raise EmbeddingsUnavailableError("zero-length embedding")
    return [x / length for x in vector]


async def post_for_vectors(
    client: httpx.AsyncClient,
    url: str,
    inputs: list[str],
    *,
    timeout: float,
    headers: dict[str, str] | None = None,
) -> list[list[float]]:
    """POST {"inputs", "normalize"} and return one checked, unit-length vector per input.

    Any failure becomes EmbeddingsUnavailableError. Only the exception class is chained, so a
    token in a header can never reach a log line through our message.
    """
    try:
        response = await client.post(
            url, json={"inputs": inputs, "normalize": True}, headers=headers, timeout=timeout
        )
        response.raise_for_status()
        body = response.json()
        # normalize=true is asked of the server, but we do not trust it: normalize again here.
        vectors = [l2_normalize([float(x) for x in row]) for row in body]
    except EmbeddingsUnavailableError:
        raise
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise EmbeddingsUnavailableError(
            f"embedding request failed: {type(exc).__name__}"
        ) from None
    if len(vectors) != len(inputs) or any(len(v) != DIMENSIONS for v in vectors):
        raise EmbeddingsUnavailableError("embedding response has the wrong shape")
    return vectors
