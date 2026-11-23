"""The chat turn (PROPOSAL §6.7, §9.4, §9.8).

One turn: check the kill switch, ownership and limits; build the prompt (system prompt,
evidence, last 12 messages, the new message); let the model call tools for at most
3 rounds; save both messages with usage. If the model is unavailable nothing is saved,
so a failed turn does not use up the daily quota.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError
from app.integrations.llm.prompts import PROMPT_VERSION, evidence_message, render_system_prompt
from app.integrations.llm.types import ChatMessage as LLMMessage
from app.integrations.llm.types import LLMClient, LLMResult
from app.modules.agent import registry
from app.modules.auth.dependencies import Scope
from app.modules.chat import repositories
from app.modules.chat.models import ChatMessage, ChatSession
from app.modules.chat.schemas import ChatReply, TokenUsage, ToolUse
from app.modules.users.models import User

HISTORY_MESSAGES = 12
MAX_TOOL_ROUNDS = 3
PER_MINUTE_LIMIT = 6
FALLBACK_REPLY = (
    "I couldn't finish that request. Please try again, or contact the office. "
    "অনুরোধটি শেষ করতে পারিনি; আবার চেষ্টা করুন বা অফিসে যোগাযোগ করুন।"
)
# Bangladesh has no daylight saving, so a fixed +6 offset is exact and needs no tz database.
DHAKA = timezone(timedelta(hours=6))


class ChatDisabledError(AppError):
    status_code = 503
    code = "chat_disabled"


class QuotaExceededError(AppError):
    status_code = 429
    code = "quota_exceeded"


class ChatRateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"
    headers = {"Retry-After": "60"}


def day_start(now: datetime) -> datetime:
    """Midnight in Dhaka for `now`, as a UTC time: daily quotas reset then."""
    local = now.astimezone(DHAKA)
    return local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)


async def create_session(session: AsyncSession, scope: Scope) -> ChatSession:
    chat = ChatSession(user_id=scope.user_id, title="New chat")
    session.add(chat)
    await session.commit()
    await session.refresh(chat)
    return chat


async def list_sessions(session: AsyncSession, scope: Scope) -> Sequence[ChatSession]:
    return await repositories.list_sessions(session, scope)


async def _own_session(session: AsyncSession, scope: Scope, chat_id: uuid.UUID) -> ChatSession:
    chat = await repositories.get_own_session(session, scope, chat_id)
    if chat is None:
        raise NotFoundError("Chat not found.")
    return chat


async def list_messages(
    session: AsyncSession, scope: Scope, chat_id: uuid.UUID
) -> Sequence[ChatMessage]:
    await _own_session(session, scope, chat_id)
    return await repositories.list_messages(session, scope, chat_id)


async def delete_session(session: AsyncSession, scope: Scope, chat_id: uuid.UUID) -> None:
    chat = await _own_session(session, scope, chat_id)
    chat.deleted_at = datetime.now(UTC)  # soft delete: kept as the audit trail
    await session.commit()


def _quota_error(message: str, now: datetime) -> QuotaExceededError:
    error = QuotaExceededError(message)
    seconds = int((day_start(now) + timedelta(days=1) - now).total_seconds())
    error.headers = {"Retry-After": str(max(seconds, 1))}
    return error


async def _check_limits(session: AsyncSession, scope: Scope, now: datetime) -> int:
    """Raise 429 if a limit is hit; return how many messages the user has left today."""
    settings = get_settings()
    start = day_start(now)
    limit = (
        settings.chat_daily_limit_staff if scope.is_staff else settings.chat_daily_limit_customer
    )
    used_today = await repositories.count_user_messages_since(session, scope, start)
    if used_today >= limit:
        raise _quota_error("You have used today's chat messages. Try again tomorrow.", now)
    everyone = await repositories.count_user_messages_since(session, scope, start, everyone=True)
    if everyone >= settings.chat_daily_limit_global:
        raise _quota_error("The assistant is busy today. Please contact the office.", now)
    recent = await repositories.count_user_messages_since(
        session, scope, now - timedelta(minutes=1)
    )
    if recent >= PER_MINUTE_LIMIT:
        raise ChatRateLimitedError("Too many messages. Please wait a minute.")
    return limit - used_today


def _assistant_tool_message(result: LLMResult) -> LLMMessage:
    """The model's tool request, echoed back so the model can match each tool result."""
    return {
        "role": "assistant",
        "content": result.content,
        "tool_calls": [
            {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments}}
            for c in result.tool_calls
        ],
    }


async def send_message(
    session: AsyncSession, scope: Scope, user: User, chat_id: uuid.UUID, text: str, llm: LLMClient
) -> ChatReply:
    settings = get_settings()
    if not settings.chat_enabled:
        raise ChatDisabledError("The assistant is switched off for now. Please contact the office.")
    chat = await _own_session(session, scope, chat_id)
    now = datetime.now(UTC)
    left_before = await _check_limits(session, scope, now)

    history = await repositories.last_messages(session, scope, chat_id, HISTORY_MESSAGES)
    system = render_system_prompt(
        operator_name=settings.operator_name, role=scope.role, today=now.astimezone(DHAKA).date()
    )
    messages: list[LLMMessage] = [
        {"role": "system", "content": system},
        evidence_message(None),  # RAG plugs in here in Phase 5
        *({"role": m.role, "content": m.content} for m in history),
        {"role": "user", "content": text},
    ]
    tools = registry.tools_for(scope.role)
    tools_used: list[ToolUse] = []
    input_tokens = output_tokens = latency_ms = 0
    reply, model = FALLBACK_REPLY, settings.llm_model

    for _ in range(MAX_TOOL_ROUNDS):
        result = await llm.complete(messages, tools)  # LLMUnavailableError -> 503, nothing saved
        input_tokens += result.usage.input_tokens
        output_tokens += result.usage.output_tokens
        latency_ms += result.latency_ms
        model = result.model
        if not result.tool_calls:
            reply = result.content or FALLBACK_REPLY
            break
        messages.append(_assistant_tool_message(result))
        for call in result.tool_calls:
            outcome = await registry.execute(session, user, call.name, call.arguments)
            tools_used.append(ToolUse(name=call.name, ok=outcome.ok))
            messages.append({"role": "tool", "tool_call_id": call.id, "content": outcome.content})

    if not history:
        chat.title = text[:60]
    # Explicit times: the database now() is fixed for the whole transaction, so both
    # messages would tie and could list in the wrong order.
    session.add(ChatMessage(session_id=chat.id, role="user", content=text, created_at=now))
    answer = ChatMessage(
        session_id=chat.id,
        role="assistant",
        content=reply[:4000],
        tools_used=[t.model_dump() for t in tools_used],
        sources=[],
        prompt_version=PROMPT_VERSION,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        created_at=datetime.now(UTC),
    )
    session.add(answer)
    chat.updated_at = now
    await session.commit()
    return ChatReply(
        message_id=answer.id,
        content=answer.content,
        tools_used=tools_used,
        sources=[],
        usage=TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens),
        messages_left_today=left_before - 1,
    )
