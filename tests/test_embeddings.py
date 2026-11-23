"""Embedding adapters: offline via httpx.MockTransport, plus one real-TEI test (skipped if down)."""

import json
import math

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.integrations.embeddings import (
    MODEL_NAME,
    EmbeddingsUnavailableError,
    FakeEmbedder,
    build_embedder,
)
from app.integrations.embeddings.cache import CachedEmbedder
from app.integrations.embeddings.hf_inference import HFInferenceEmbedder
from app.integrations.embeddings.tei import TEIEmbedder

DIM = 384


def unit(i: int = 0, dim: int = DIM) -> list[float]:
    return [1.0 if j == i else 0.0 for j in range(dim)]


def norm(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def tei_client(handler) -> httpx.AsyncClient:  # type: ignore[no-untyped-def]
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def echo_handler(requests: list[httpx.Request]):  # type: ignore[no-untyped-def]
    """Answers every input with an un-normalized vector, so client-side normalizing is visible."""

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        inputs = json.loads(request.content)["inputs"]
        return httpx.Response(200, json=[[3.0, 4.0] + [0.0] * (DIM - 2) for _ in inputs])

    return handler


# ---------- TEI ----------


async def test_tei_sends_prefixes_and_normalize_and_returns_unit_vectors() -> None:
    seen: list[httpx.Request] = []
    embedder = TEIEmbedder("http://tei:80/", http_client=tei_client(echo_handler(seen)))

    q = await embedder.embed_query("router red light")
    p = await embedder.embed_passages(["restart the router"])

    assert embedder.model_name == MODEL_NAME
    assert str(seen[0].url) == "http://tei/embed"
    first, second = (json.loads(r.content) for r in seen)
    assert first == {"inputs": ["query: router red light"], "normalize": True}
    assert second == {"inputs": ["passage: restart the router"], "normalize": True}
    assert len(q) == DIM and norm(q) == pytest.approx(1.0)
    assert norm(p[0]) == pytest.approx(1.0)


async def test_tei_batches_70_passages_into_3_requests() -> None:
    seen: list[httpx.Request] = []
    embedder = TEIEmbedder("http://tei", http_client=tei_client(echo_handler(seen)), batch_size=32)

    vectors = await embedder.embed_passages([f"text {i}" for i in range(70)])

    assert len(vectors) == 70
    assert [len(json.loads(r.content)["inputs"]) for r in seen] == [32, 32, 6]


async def test_tei_empty_passages_makes_no_request() -> None:
    seen: list[httpx.Request] = []
    embedder = TEIEmbedder("http://tei", http_client=tei_client(echo_handler(seen)))
    assert await embedder.embed_passages([]) == []
    assert seen == []


def _raise_timeout(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectTimeout("slow", request=request)


@pytest.mark.parametrize(
    "handler",
    [
        lambda r: httpx.Response(500, text="boom"),
        _raise_timeout,
        lambda r: httpx.Response(200, content=b"not json at all"),
        lambda r: httpx.Response(200, json=[[0.1] * 383]),
        lambda r: httpx.Response(200, json={"error": "shape"}),
        lambda r: httpx.Response(200, json=[]),  # fewer vectors than inputs
        lambda r: httpx.Response(200, json=[[0.0] * DIM]),  # cannot normalize a zero vector
    ],
    ids=["http500", "timeout", "bad_json", "dim_383", "wrong_shape", "count_mismatch", "zero"],
)
async def test_tei_failures_raise_unavailable(handler) -> None:  # type: ignore[no-untyped-def]
    embedder = TEIEmbedder("http://tei", http_client=tei_client(handler))
    with pytest.raises(EmbeddingsUnavailableError):
        await embedder.embed_query("hello")
    with pytest.raises(EmbeddingsUnavailableError):
        await embedder.embed_passages(["hello"])


# ---------- Hugging Face Inference ----------


async def test_hf_sends_bearer_header_and_parses_response() -> None:
    seen: list[httpx.Request] = []
    embedder = HFInferenceEmbedder("hf_secret", http_client=tei_client(echo_handler(seen)))

    vec = await embedder.embed_query("hello")

    assert embedder.model_name == MODEL_NAME
    assert seen[0].headers["Authorization"] == "Bearer hf_secret"
    assert seen[0].url.host == "router.huggingface.co"
    assert seen[0].url.path.endswith("/intfloat/multilingual-e5-small/pipeline/feature-extraction")
    assert json.loads(seen[0].content) == {"inputs": ["query: hello"], "normalize": True}
    assert len(vec) == DIM and norm(vec) == pytest.approx(1.0)


async def test_hf_http_error_raises_unavailable() -> None:
    embedder = HFInferenceEmbedder("t", http_client=tei_client(lambda r: httpx.Response(401)))
    with pytest.raises(EmbeddingsUnavailableError):
        await embedder.embed_passages(["x"])


async def test_missing_hf_token_raises_at_call_time_not_at_build() -> None:
    settings = Settings(embeddings_provider="hf_inference", hf_token=None)  # type: ignore[call-arg]
    embedder = build_embedder(settings)  # must not raise
    with pytest.raises(EmbeddingsUnavailableError):
        await embedder.embed_query("hello")
    with pytest.raises(EmbeddingsUnavailableError):
        await embedder.embed_passages(["hello"])


# ---------- Fake ----------


async def test_fake_is_deterministic_384_dim_unit_norm() -> None:
    fake = FakeEmbedder()
    a = await fake.embed_query("My router light is red")
    b = await fake.embed_query("My router light is red")
    assert a == b and len(a) == DIM and norm(a) == pytest.approx(1.0)
    assert fake.model_name == "fake-e5-384" != MODEL_NAME


async def test_fake_empty_text_is_a_fixed_unit_vector() -> None:
    fake = FakeEmbedder()
    a, b = await fake.embed_query(""), await fake.embed_query("  !!  ")
    assert a == b and norm(a) == pytest.approx(1.0)


async def test_fake_handles_bangla_and_ignores_prefixes() -> None:
    fake = FakeEmbedder()
    q = await fake.embed_query("রাউটারে লাল বাতি জ্বলছে")
    (p,) = await fake.embed_passages(["রাউটারে লাল বাতি জ্বলছে"])
    assert norm(q) == pytest.approx(1.0)
    assert cosine(q, p) == pytest.approx(1.0)
    assert cosine(q, await fake.embed_query("অফিস সময় সকাল নয়টা")) < 0.5


async def test_fake_shared_words_are_closer_than_unrelated() -> None:
    fake = FakeEmbedder()
    q = await fake.embed_query("router red light blinking")
    near = await fake.embed_query("red light on the router")
    far = await fake.embed_query("office opens at nine every morning")
    assert cosine(q, near) > cosine(q, far)


# ---------- Cache ----------


class CountingEmbedder:
    model_name = "counting"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.query_calls: list[str] = []
        self.passage_calls = 0

    async def embed_query(self, text: str) -> list[float]:
        self.query_calls.append(text)
        if self.fail:
            raise EmbeddingsUnavailableError()
        return unit(len(self.query_calls))

    async def embed_passages(self, texts: list[str]) -> list[list[float]]:
        self.passage_calls += 1
        return [unit(0) for _ in texts]


async def test_cache_hit_skips_inner() -> None:
    inner = CountingEmbedder()
    cached = CachedEmbedder(inner)
    first = await cached.embed_query("a")
    second = await cached.embed_query("a")
    assert first == second
    assert inner.query_calls == ["a"]
    assert cached.cache_info() == (1, 1)
    assert cached.model_name == "counting"


async def test_cache_evicts_oldest_past_maxsize_and_refreshes_on_hit() -> None:
    inner = CountingEmbedder()
    cached = CachedEmbedder(inner, maxsize=2)
    await cached.embed_query("a")
    await cached.embed_query("b")
    await cached.embed_query("a")  # hit: "a" becomes newest, "b" oldest
    await cached.embed_query("c")  # evicts "b"
    await cached.embed_query("a")  # still cached
    await cached.embed_query("b")  # was evicted: inner called again
    assert inner.query_calls == ["a", "b", "c", "b"]


async def test_cache_does_not_cache_failures() -> None:
    inner = CountingEmbedder(fail=True)
    cached = CachedEmbedder(inner)
    for _ in range(2):
        with pytest.raises(EmbeddingsUnavailableError):
            await cached.embed_query("a")
    assert inner.query_calls == ["a", "a"]
    inner.fail = False
    await cached.embed_query("a")
    await cached.embed_query("a")
    assert inner.query_calls == ["a", "a", "a"]


async def test_cache_passages_bypass_cache() -> None:
    inner = CountingEmbedder()
    cached = CachedEmbedder(inner)
    await cached.embed_passages(["a"])
    await cached.embed_passages(["a"])
    assert inner.passage_calls == 2
    assert cached.cache_info() == (0, 0)


# ---------- build_embedder ----------


def test_build_embedder_picks_each_provider() -> None:
    tei = build_embedder(Settings(embeddings_provider="tei", embeddings_url="http://x:80"))  # type: ignore[call-arg]
    hf = build_embedder(Settings(embeddings_provider="hf_inference", hf_token=SecretStr("t")))  # type: ignore[call-arg]
    fake = build_embedder(Settings(embeddings_provider="fake"))  # type: ignore[call-arg]
    assert all(isinstance(e, CachedEmbedder) for e in (tei, hf, fake))
    assert isinstance(tei._inner, TEIEmbedder) and tei.model_name == MODEL_NAME  # type: ignore[attr-defined]
    assert isinstance(hf._inner, HFInferenceEmbedder)  # type: ignore[attr-defined]
    assert isinstance(fake._inner, FakeEmbedder) and fake.model_name == "fake-e5-384"  # type: ignore[attr-defined]


# ---------- Real TEI (skipped when it is not running) ----------

REAL_TEI = "http://127.0.0.1:8080"


async def test_real_tei_bangla_question_is_closer_to_matching_passage() -> None:
    try:
        httpx.get(f"{REAL_TEI}/health", timeout=1.0).raise_for_status()
    except httpx.HTTPError:
        pytest.skip("TEI is not running at 127.0.0.1:8080")

    embedder = TEIEmbedder(REAL_TEI)
    question = await embedder.embed_query("আমার রাউটারে লাল বাতি জ্বলছে, কী করব?")
    router, office = await embedder.embed_passages(
        [
            "If the router shows a red light, restart it and check the fibre cable.",
            "Our office is open from 9 am to 6 pm, Saturday to Thursday.",
        ]
    )
    assert len(question) == DIM and norm(question) == pytest.approx(1.0, abs=1e-5)
    assert cosine(question, router) > cosine(question, office)
