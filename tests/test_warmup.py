"""Startup warm-up (PROPOSAL §12.3.5): on Render both the API and the embedder sleep when
idle, so the API's startup sends one embedding call in the background. Both then wake
together, instead of the first chat question waiting for the embedder's cold start."""

import asyncio

import pytest

from app import main
from app.integrations.embeddings import EmbeddingsUnavailableError


class Recorder:
    model_name = "test"

    def __init__(self, fail: bool = False) -> None:
        self.calls: list[str] = []
        self.fail = fail

    async def embed_query(self, text: str) -> list[float]:
        self.calls.append(text)
        if self.fail:
            raise EmbeddingsUnavailableError("down")
        return [0.0]

    async def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] for _ in texts]


@pytest.mark.parametrize("fail", [False, True])
async def test_startup_wakes_the_embedder_without_blocking_or_crashing(
    monkeypatch: pytest.MonkeyPatch, fail: bool
) -> None:
    recorder = Recorder(fail=fail)
    monkeypatch.setattr(main, "get_embedder", lambda: recorder)
    app = main.create_app()

    async with app.router.lifespan_context(app):
        await asyncio.sleep(0.05)  # let the background warm-up run

    assert recorder.calls == ["warm up"]  # an embedder that is down never stops startup
