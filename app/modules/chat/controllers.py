import uuid
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.integrations.embeddings import Embedder, get_embedder
from app.integrations.llm.client import get_llm_client
from app.integrations.llm.types import LLMClient
from app.modules.auth.dependencies import CurrentScope, CurrentUser
from app.modules.chat import services
from app.modules.chat.models import ChatMessage, ChatSession
from app.modules.chat.schemas import (
    ChatMessageCreate,
    ChatReply,
    ChatUsage,
    MessageRead,
    SessionRead,
)

router = APIRouter(prefix="/chat/sessions", tags=["chat"])
usage_router = APIRouter(prefix="/chat", tags=["chat"])

Session = Annotated[AsyncSession, Depends(get_session)]
LLM = Annotated[LLMClient, Depends(get_llm_client)]
EmbedderDep = Annotated[Embedder, Depends(get_embedder)]


@router.post("", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
async def create_session(session: Session, scope: CurrentScope) -> ChatSession:
    return await services.create_session(session, scope)


@router.get("", response_model=list[SessionRead])
async def list_sessions(session: Session, scope: CurrentScope) -> Sequence[ChatSession]:
    return await services.list_sessions(session, scope)


@router.get("/{chat_id}/messages", response_model=list[MessageRead])
async def list_messages(
    session: Session, scope: CurrentScope, chat_id: uuid.UUID
) -> Sequence[ChatMessage]:
    return await services.list_messages(session, scope, chat_id)


@router.post("/{chat_id}/messages", response_model=ChatReply, status_code=status.HTTP_201_CREATED)
async def send_message(
    session: Session,
    scope: CurrentScope,
    user: CurrentUser,
    llm: LLM,
    embedder: EmbedderDep,
    chat_id: uuid.UUID,
    body: ChatMessageCreate,
) -> ChatReply:
    return await services.send_message(session, scope, user, chat_id, body.content, llm, embedder)


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session: Session, scope: CurrentScope, chat_id: uuid.UUID) -> Response:
    await services.delete_session(session, scope, chat_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@usage_router.get("/usage", response_model=ChatUsage)
async def get_usage(session: Session, scope: CurrentScope) -> ChatUsage:
    return await services.usage(session, scope)
