import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.modules.billing.models import BillStatus, PaymentMethod

# "YYYY-MM" with a month from 01 to 12; the same rule as the bills.period CHECK.
PERIOD_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"
# Strip and upper-case first, so " abc123x " is stored as "ABC123X" and counts as the same TrxID.
TrxId = Annotated[
    str, StringConstraints(strip_whitespace=True, to_upper=True, min_length=4, max_length=40)
]


class GenerateBills(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: Annotated[str, StringConstraints(pattern=PERIOD_PATTERN)]


class GenerateResult(BaseModel):
    period: str
    created: int
    skipped: int


class PaymentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trx_id: TrxId
    payment_method: PaymentMethod


class BillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    connection_id: uuid.UUID
    period: str
    amount_bdt: Decimal
    due_date: date
    status: BillStatus
    paid_at: datetime | None
    payment_method: PaymentMethod | None
    trx_id: str | None


class AreaDues(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    area_id: int
    area_code: str
    unpaid_count: int
    unpaid_total_bdt: Decimal
