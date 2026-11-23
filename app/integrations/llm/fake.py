"""A scripted LLM for tests: no network, answers come from a list."""

import json
from typing import Any

from app.integrations.llm.client import LLMUnavailableError
from app.integrations.llm.types import ChatMessage, LLMResult, ToolCall, ToolSpec, Usage


class FakeLLM:
    def __init__(self, script: list[LLMResult], *, fail: bool = False) -> None:
        self._script = list(script)
        self._fail = fail
        self.calls: list[tuple[list[ChatMessage], list[ToolSpec]]] = []

    async def complete(
        self, messages: list[ChatMessage], tools: list[ToolSpec], *, max_tokens: int = 600
    ) -> LLMResult:
        self.calls.append((list(messages), list(tools)))
        if self._fail:
            raise LLMUnavailableError()
        if not self._script:
            raise AssertionError(
                f"FakeLLM script ran out: complete() was called {len(self.calls)} times"
            )
        return self._script.pop(0)

    @staticmethod
    def text(content: str, *, input_tokens: int = 100, output_tokens: int = 20) -> LLMResult:
        return LLMResult(content, [], Usage(input_tokens, output_tokens), "fake-model", 1)

    @staticmethod
    def tool(name: str, arguments: dict[str, Any], *, call_id: str = "call_1") -> LLMResult:
        call = ToolCall(call_id, name, json.dumps(arguments))
        return LLMResult(None, [call], Usage(100, 20), "fake-model", 1)
