"""Business rules for notices. Services own the transaction and call commit."""

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFoundError
from app.modules.auth.dependencies import Scope
from app.modules.notices import repositories
from app.modules.notices.models import AreaNotice
from app.modules.notices.schemas import NoticeCreate, NoticeUpdate


class InvalidNoticePeriodError(AppError):
    """A PATCH that leaves ends_at at or before starts_at (a POST is caught by the schema)."""

    status_code = 422
    code = "validation_error"


async def list_notices(
    session: AsyncSession, scope: Scope, area_id: int | None, active: bool | None
) -> Sequence[AreaNotice]:
    return await repositories.list_notices(session, scope, area_id, active)


async def _require_area(session: AsyncSession, scope: Scope, area_id: int) -> None:
    if not await repositories.area_exists(session, scope, area_id):
        raise NotFoundError("Area not found.")


async def create_notice(session: AsyncSession, scope: Scope, data: NoticeCreate) -> AreaNotice:
    await _require_area(session, scope, data.area_id)
    notice = AreaNotice(**data.model_dump(), created_by=scope.user_id)
    session.add(notice)
    await session.commit()
    return notice


async def update_notice(
    session: AsyncSession, scope: Scope, notice_id: uuid.UUID, data: NoticeUpdate
) -> AreaNotice:
    notice = await repositories.get_notice(session, scope, notice_id)
    if notice is None:
        raise NotFoundError("Notice not found.")
    # exclude_none: an explicit null means "no change"; none of these columns is nullable.
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if "area_id" in changes:
        await _require_area(session, scope, changes["area_id"])
    # Check the merged times before touching the object, so a rejected PATCH leaves it clean.
    if changes.get("ends_at", notice.ends_at) <= changes.get("starts_at", notice.starts_at):
        raise InvalidNoticePeriodError("ends_at must be after starts_at.")
    for field, value in changes.items():
        setattr(notice, field, value)
    await session.commit()
    return notice
