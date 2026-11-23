"""The real LLM client: the openai SDK pointed at any OpenAI-compatible endpoint (Gemini)."""

import logging
import time
from functools import lru_cache
from typing import Any

import openai

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.integrations.llm.types import ChatMessage, LLMClient, LLMResult, ToolCall, ToolSpec, Usage

logger = logging.getLogger(__name__)


class LLMUnavailableError(AppError):
    """The model could not answer (down, slow, rate-limited, not configured): HTTP 503."""

    status_code = 503
    code = "llm_unavailable"

    def __init__(
        self, message: str = "The assistant is temporarily unavailable. Please try again shortly."
    ) -> None:
        super().__init__(message)


class OpenAICompatClient:
    def __init__(
        self,
        settings: Settings,
        *,
        http_client: openai.DefaultAsyncHttpxClient | None = None,
        max_retries: int = 2,
    ) -> None:
        self._model = settings.llm_model
        key = settings.llm_api_key
        self._configured = key is not None
        # The SDK needs a key string to build; `complete` refuses before any call if none is set.
        self._sdk = openai.AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=key.get_secret_value() if key else "not-configured",
            timeout=20.0,
            max_retries=max_retries,  # SDK retries 429/5xx/timeouts with backoff
            http_client=http_client,
        )

    async def complete(
        self, messages: list[ChatMessage], tools: list[ToolSpec], *, max_tokens: int = 600
    ) -> LLMResult:
        if not self._configured:
            raise LLMUnavailableError("The assistant is not configured.")
        started = time.perf_counter()
        params: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if tools:
            params["tools"] = tools
        try:
            response = await self._sdk.chat.completions.create(**params)
        except openai.APIError as exc:
            # Class name and status only: never message content or the key.
            logger.warning(
                "LLM call failed: %s status=%s",
                type(exc).__name__,
                getattr(exc, "status_code", None),
            )
            raise LLMUnavailableError() from exc
        latency_ms = int((time.perf_counter() - started) * 1000)

        message = response.choices[0].message
        tool_calls = [
            ToolCall(id=call.id, name=call.function.name, arguments=call.function.arguments)
            for call in message.tool_calls or []
            if call.type == "function"
        ]
        usage = response.usage
        return LLMResult(
            content=message.content,
            tool_calls=tool_calls,
            usage=Usage(
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
            ),
            model=response.model,
            latency_ms=latency_ms,
        )


@lru_cache
def get_llm_client() -> LLMClient:
    """FastAPI dependency for the chat module; tests override it with a FakeLLM."""
    return OpenAICompatClient(get_settings())
