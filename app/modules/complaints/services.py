"""Business rules for complaints. Services own the transaction and call commit."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.core.pagination import Page, PageParams
from app.modules.auth.dependencies import Scope
from app.modules.complaints import repositories
from app.modules.complaints.models import Complaint
from app.modules.complaints.schemas import ComplaintCreate, ComplaintRead, ComplaintUpdate
from app.modules.connections import services as connection_services

# The only moves a ticket may make. Same-status and every other change is a 409.
ALLOWED_TRANSITIONS = {
    ("open", "in_progress"),
    ("in_progress", "resolved"),
    ("resolved", "closed"),
    ("resolved", "in_progress"),  # reopened: the fix did not hold
}


async def list_complaints(
    session: AsyncSession,
    scope: Scope,
    page: PageParams,
    *,
    status: str | None,
    area_id: int | None,
) -> Page[ComplaintRead]:
    items, total = await repositories.list_complaints(
        session, scope, page, status=status, area_id=area_id
    )
    return Page[ComplaintRead](
        items=[ComplaintRead.model_validate(c) for c in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


async def create_complaint(session: AsyncSession, scope: Scope, data: ComplaintCreate) -> Complaint:
    if scope.role == "customer" and not get_settings().allow_customer_complaints:
        raise ForbiddenError("Complaints are created by the ISP office.")
    # Scoped lookup: a customer gets 404 for a connection that is not theirs.
    await connection_services.get_connection(session, scope, data.connection_id)
    complaint = Complaint(**data.model_dump(), created_by=scope.user_id)
    session.add(complaint)
    await session.commit()
    return complaint


async def update_complaint(
    session: AsyncSession, scope: Scope, complaint_id: uuid.UUID, data: ComplaintUpdate
) -> Complaint:
    complaint = await repositories.get_complaint(session, scope, complaint_id)
    if complaint is None:
        raise NotFoundError("Complaint not found.")

    changes = data.model_dump(exclude_unset=True)
    if changes.get("status") is None:
        changes.pop("status", None)  # an explicit null means "no change"

    if "assigned_to" in changes:
        if scope.role != "admin":
            raise ForbiddenError("Only an admin can assign a complaint.")
        technician_id = changes["assigned_to"]
        if technician_id is not None and not await repositories.technician_exists(
            session, scope, technician_id
        ):
            raise NotFoundError("Technician not found.")

    new_status = changes.get("status")
    if new_status is not None and (complaint.status, new_status) not in ALLOWED_TRANSITIONS:
        raise ConflictError(f"Cannot change status from {complaint.status} to {new_status}.")

    for field, value in changes.items():
        setattr(complaint, field, value)
    await session.commit()
    await session.refresh(complaint)  # updated_at is set by the database on UPDATE
    return complaint
