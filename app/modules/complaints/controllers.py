"""HTTP only: parse input, check the role, call the service, shape the response."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import Page, PageQuery
from app.modules.auth.dependencies import CurrentScope, require_roles
from app.modules.complaints import services
from app.modules.complaints.models import Complaint, ComplaintStatus
from app.modules.complaints.schemas import ComplaintCreate, ComplaintRead, ComplaintUpdate

router = APIRouter(prefix="/complaints", tags=["complaints"])

Session = Annotated[AsyncSession, Depends(get_session)]
CanCreate = [Depends(require_roles("customer", "admin"))]
StaffOnly = [Depends(require_roles("technician", "admin"))]


@router.get("", response_model=Page[ComplaintRead])
async def list_complaints(
    session: Session,
    scope: CurrentScope,
    page: PageQuery,
    status: ComplaintStatus | None = None,
    area_id: int | None = None,
) -> Page[ComplaintRead]:
    return await services.list_complaints(session, scope, page, status=status, area_id=area_id)


@router.post(
    "", response_model=ComplaintRead, status_code=status.HTTP_201_CREATED, dependencies=CanCreate
)
async def create_complaint(
    session: Session, scope: CurrentScope, body: ComplaintCreate
) -> Complaint:
    return await services.create_complaint(session, scope, body)


@router.patch("/{complaint_id}", response_model=ComplaintRead, dependencies=StaffOnly)
async def update_complaint(
    session: Session, scope: CurrentScope, complaint_id: uuid.UUID, body: ComplaintUpdate
) -> Complaint:
    return await services.update_complaint(session, scope, complaint_id, body)
