"""Business rules for bills. Services own the transaction and call commit."""

import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.modules.auth.dependencies import Scope
from app.modules.billing import repositories
from app.modules.billing.models import Bill
from app.modules.billing.schemas import GenerateResult, PaymentCreate

TRX_USED = "This TrxID was already used."


def due_date_for(period: str) -> date:
    """The 10th of the month after `period` ("YYYY-MM"); December rolls into January."""
    year, month = (int(part) for part in period.split("-"))
    if month == 12:
        return date(year + 1, 1, 10)
    return date(year, month + 1, 10)


async def generate_bills(session: AsyncSession, scope: Scope, period: str) -> GenerateResult:
    billable = await repositories.count_billable_connections(session, scope)
    created = await repositories.insert_bills(session, scope, period, due_date_for(period))
    await session.commit()
    return GenerateResult(period=period, created=created, skipped=billable - created)


async def list_bills(
    session: AsyncSession,
    scope: Scope,
    *,
    connection_id: uuid.UUID | None,
    period: str | None,
    status: str | None,
    limit: int,
    offset: int,
) -> tuple[Sequence[Bill], int]:
    return await repositories.list_bills(
        session,
        scope,
        connection_id=connection_id,
        period=period,
        status=status,
        limit=limit,
        offset=offset,
    )


async def record_payment(
    session: AsyncSession, scope: Scope, bill_id: uuid.UUID, data: PaymentCreate
) -> Bill:
    bill = await repositories.get_bill_for_update(session, scope, bill_id)
    if bill is None:
        raise NotFoundError("Bill not found.")
    if bill.status == "paid":
        raise ConflictError("This bill is already paid.")
    if bill.status == "waived":
        raise ConflictError("This bill was waived.")
    if await repositories.trx_id_used(session, scope, data.trx_id):
        raise ConflictError(TRX_USED)
    bill.status = "paid"
    bill.paid_at = datetime.now(UTC)
    bill.verified_by = scope.user_id
    bill.payment_method = data.payment_method
    bill.trx_id = data.trx_id
    try:
        await session.commit()
    except IntegrityError:
        # Another request saved the same TrxID after our check; the unique index decides.
        await session.rollback()
        raise ConflictError(TRX_USED) from None
    return bill


async def unpaid_summary(session: AsyncSession, scope: Scope, period: str) -> Sequence[Any]:
    return await repositories.unpaid_by_area(session, scope, period)
