import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, get_args

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.connections.models import _in_list

BillStatus = Literal["unpaid", "paid", "waived"]
PaymentMethod = Literal["bkash", "nagad", "cash", "bank"]


class Bill(Base):
    """A monthly due for one connection, plus its payment trail (PROPOSAL §7.2).

    Migration 0001 creates the bill; 0002_payment_trail adds payment_method, trx_id,
    verified_by and the paid-means-paid_at rule.
    """

    __tablename__ = "bills"
    __table_args__ = (
        UniqueConstraint("connection_id", "period", name="uq_bills_connection_id_period"),
        CheckConstraint(r"period ~ '^\d{4}-(0[1-9]|1[0-2])$'", name="period_format"),
        CheckConstraint("amount_bdt >= 0", name="amount_not_negative"),
        CheckConstraint(_in_list("status", get_args(BillStatus)), name="status_valid"),
        Index("ix_bills_status_period", "status", "period"),
        Index("ix_bills_connection_id", "connection_id"),
        # --- payment trail (0002) ---
        CheckConstraint(
            "payment_method IS NULL OR " + _in_list("payment_method", get_args(PaymentMethod)),
            name="payment_method_valid",
        ),
        CheckConstraint("(status = 'paid') = (paid_at IS NOT NULL)", name="paid_means_paid_at"),
        # A TrxID can be used once; unpaid bills have none (partial unique index).
        Index(
            "uq_bills_trx_id",
            "trx_id",
            unique=True,
            postgresql_where=text("trx_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connections.id", ondelete="RESTRICT")
    )
    # Billing month as "YYYY-MM".
    period: Mapped[str] = mapped_column(String(7))
    amount_bdt: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    # The 10th of the month after `period` (PROPOSAL §7.2).
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(
        String(8), default="unpaid", server_default=text("'unpaid'")
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # --- payment trail (0002) ---
    payment_method: Mapped[str | None] = mapped_column(String(10))
    trx_id: Mapped[str | None] = mapped_column(String(40))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
