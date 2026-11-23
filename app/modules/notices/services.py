"""Business rules for notices. Services own the transaction and call commit."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

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


async def area_status(
    session: AsyncSession, scope: Scope, *, area_code: str | None = None
) -> dict[str, Any]:
    """Outage picture of one area for the agent tools. A customer gets the area of their
    own connection (`area_code` is ignored); staff must name an area."""
    area = await repositories.find_area_for_status(session, scope, area_code)
    if area is None:
        code = "unknown_area" if scope.is_staff else "no_connection"
        raise NotFoundError("Area not found.", details={"code": code})
    notices = await repositories.active_notices(session, scope, area.id)
    result: dict[str, Any] = {
        "area_code": area.code,
        "area_name": area.name,
        "area_name_bn": area.name_bn,
        "active_notices": [
            {
                "kind": n.kind,
                "message_bn": n.message_bn,
                "message_en": n.message_en,
                "ends_at": n.ends_at.isoformat(),
            }
            for n in notices
        ],
    }
    if not scope.is_staff:
        mine = await repositories.my_open_complaints(session, scope)
        result["open_complaints_in_area"] = await repositories.open_complaint_count(
            session, scope, area.id
        )
        result["my_open_complaints"] = [
            {"category": c.category, "status": c.status, "created_at": c.created_at.isoformat()}
            for c in mine
        ]
        return result
    oldest = await repositories.oldest_open_complaint_at(session, scope, area.id)
    result["open_complaints_by_category"] = await repositories.open_complaints_by_category(
        session, scope, area.id
    )
    result["oldest_open_complaint_hours"] = (
        None if oldest is None else int((datetime.now(UTC) - oldest).total_seconds() // 3600)
    )
    return result
