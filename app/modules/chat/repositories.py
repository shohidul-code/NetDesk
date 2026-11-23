"""SQL for chat. Every lookup is limited to the caller's own sessions (Scope.user_id),
so another user's session id behaves exactly like a missing one (404)."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import Scope
from app.modules.chat.models import ChatMessage, ChatSession


async def list_sessions(session: AsyncSession, scope: Scope) -> Sequence[ChatSession]:
    query = (
        select(ChatSession)
        .where(ChatSession.user_id == scope.user_id, ChatSession.deleted_at.is_(None))
        .order_by(ChatSession.updated_at.desc(), ChatSession.id)
    )
    return (await session.execute(query)).scalars().all()


async def get_own_session(
    session: AsyncSession, scope: Scope, chat_id: uuid.UUID
) -> ChatSession | None:
    query = select(ChatSession).where(
        ChatSession.id == chat_id,
        ChatSession.user_id == scope.user_id,
        ChatSession.deleted_at.is_(None),
    )
    return (await session.execute(query)).scalar_one_or_none()


async def list_messages(
    session: AsyncSession, scope: Scope, chat_id: uuid.UUID
) -> Sequence[ChatMessage]:
    query = (
        select(ChatMessage)
        .join(ChatSession)
        .where(ChatMessage.session_id == chat_id, ChatSession.user_id == scope.user_id)
        .order_by(ChatMessage.created_at, ChatMessage.id)
    )
    return (await session.execute(query)).scalars().all()


async def last_messages(
    session: AsyncSession, scope: Scope, chat_id: uuid.UUID, limit: int
) -> list[ChatMessage]:
    """The newest `limit` messages, returned oldest first (the order the model reads)."""
    query = (
        select(ChatMessage)
        .join(ChatSession)
        .where(ChatMessage.session_id == chat_id, ChatSession.user_id == scope.user_id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(limit)
    )
    return list(reversed((await session.execute(query)).scalars().all()))


async def count_user_messages_since(
    session: AsyncSession, scope: Scope, since: datetime, *, everyone: bool = False
) -> int:
    """Messages the user (or, with everyone=True, all users) sent since `since`."""
    query = (
        select(func.count())
        .select_from(ChatMessage)
        .join(ChatSession)
        .where(ChatMessage.role == "user", ChatMessage.created_at >= since)
    )
    if not everyone:
        query = query.where(ChatSession.user_id == scope.user_id)
    return (await session.execute(query)).scalar_one()
