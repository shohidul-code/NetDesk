"""payment trail: payment_method, trx_id (unique when present), verified_by, paid => paid_at.

A separate migration on purpose: it shows the schema evolving on a table that already
has rows (PROPOSAL §7.4).

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("bills", sa.Column("payment_method", sa.String(length=10), nullable=True))
    op.add_column("bills", sa.Column("trx_id", sa.String(length=40), nullable=True))
    op.add_column("bills", sa.Column("verified_by", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_bills_verified_by_users"),
        "bills",
        "users",
        ["verified_by"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        op.f("ck_bills_payment_method_valid"),
        "bills",
        "payment_method IS NULL OR payment_method IN ('bkash', 'nagad', 'cash', 'bank')",
    )
    op.create_check_constraint(
        op.f("ck_bills_paid_means_paid_at"),
        "bills",
        "(status = 'paid') = (paid_at IS NOT NULL)",
    )
    # A TrxID can be used once; bills without one are not compared.
    op.create_index(
        "uq_bills_trx_id",
        "bills",
        ["trx_id"],
        unique=True,
        postgresql_where=sa.text("trx_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_bills_trx_id", table_name="bills", postgresql_where=sa.text("trx_id IS NOT NULL")
    )
    op.drop_constraint(op.f("ck_bills_paid_means_paid_at"), "bills", type_="check")
    op.drop_constraint(op.f("ck_bills_payment_method_valid"), "bills", type_="check")
    op.drop_constraint(op.f("fk_bills_verified_by_users"), "bills", type_="foreignkey")
    op.drop_column("bills", "verified_by")
    op.drop_column("bills", "trx_id")
    op.drop_column("bills", "payment_method")
