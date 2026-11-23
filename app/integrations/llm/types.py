"""Shapes shared by every LLM client. Messages stay plain OpenAI-format dicts."""

from dataclasses import dataclass
from typing import Any, Protocol

ChatMessage = dict[str, Any]
ToolSpec = dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: str  # raw JSON string from the model; the caller validates it with Pydantic


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class LLMResult:
    content: str | None
    tool_calls: list[ToolCall]
    usage: Usage
    model: str
    latency_ms: int


class LLMClient(Protocol):
    async def complete(
        self, messages: list[ChatMessage], tools: list[ToolSpec], *, max_tokens: int = 600
    ) -> LLMResult: ...
