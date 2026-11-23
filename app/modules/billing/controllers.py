"""HTTP only: parse input, check the role, call the service, shape the response."""

import uuid
from collections.abc import Sequence
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import Page, PageQuery
from app.modules.auth.dependencies import CurrentScope, require_roles
from app.modules.billing import services
from app.modules.billing.models import Bill, BillStatus
from app.modules.billing.schemas import (
    PERIOD_PATTERN,
    AreaDues,
    BillRead,
    GenerateBills,
    GenerateResult,
    PaymentCreate,
)

router = APIRouter(prefix="/bills", tags=["bills"])

Session = Annotated[AsyncSession, Depends(get_session)]
AdminOnly = [Depends(require_roles("admin"))]
PeriodQuery = Annotated[str, Query(pattern=PERIOD_PATTERN)]


@router.post(
    "/generate",
    response_model=GenerateResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=AdminOnly,
)
async def generate_bills(session: Session, scope: CurrentScope, body: GenerateBills) -> Any:
    return await services.generate_bills(session, scope, body.period)


# Declared before any "/{id}" route so "summary" is never read as an id.
@router.get("/summary", response_model=list[AreaDues], dependencies=AdminOnly)
async def unpaid_summary(
    session: Session, scope: CurrentScope, period: PeriodQuery
) -> Sequence[Any]:
    return await services.unpaid_summary(session, scope, period)


@router.get("", response_model=Page[BillRead])
async def list_bills(
    session: Session,
    scope: CurrentScope,
    page: PageQuery,
    connection_id: uuid.UUID | None = None,
    period: Annotated[str | None, Query(pattern=PERIOD_PATTERN)] = None,
    status: BillStatus | None = None,
) -> Any:
    items, total = await services.list_bills(
        session,
        scope,
        connection_id=connection_id,
        period=period,
        status=status,
        limit=page.limit,
        offset=page.offset,
    )
    return Page(items=list(items), total=total, limit=page.limit, offset=page.offset)


@router.post("/{bill_id}/payment", response_model=BillRead, dependencies=AdminOnly)
async def record_payment(
    session: Session, scope: CurrentScope, bill_id: uuid.UUID, body: PaymentCreate
) -> Bill:
    return await services.record_payment(session, scope, bill_id, body)
