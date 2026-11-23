"""HTTP only: parse input, check the role, call the service, shape the response."""

import uuid
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.modules.auth.dependencies import CurrentScope, require_roles
from app.modules.notices import services
from app.modules.notices.models import AreaNotice
from app.modules.notices.schemas import NoticeCreate, NoticeRead, NoticeUpdate

router = APIRouter(prefix="/notices", tags=["notices"])

Session = Annotated[AsyncSession, Depends(get_session)]
AdminOnly = [Depends(require_roles("admin"))]


@router.get("", response_model=list[NoticeRead])
async def list_notices(
    session: Session, scope: CurrentScope, area_id: int | None = None, active: bool | None = None
) -> Sequence[AreaNotice]:
    return await services.list_notices(session, scope, area_id, active)


@router.post(
    "", response_model=NoticeRead, status_code=status.HTTP_201_CREATED, dependencies=AdminOnly
)
async def create_notice(session: Session, scope: CurrentScope, body: NoticeCreate) -> AreaNotice:
    return await services.create_notice(session, scope, body)


@router.patch("/{notice_id}", response_model=NoticeRead, dependencies=AdminOnly)
async def update_notice(
    session: Session, scope: CurrentScope, notice_id: uuid.UUID, body: NoticeUpdate
) -> AreaNotice:
    return await services.update_notice(session, scope, notice_id, body)
