"""Add M-Pesa STK Push payment data and booking commission amounts

Revision ID: 65c4d9a1f2b7
Revises: 8baf0d7c3912
Create Date: 2026-11-06 08:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "65c4d9a1f2b7"
down_revision: Union[str, None] = "8baf0d7c3912"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bookings",
        sa.Column("commission_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "bookings",
        sa.Column("owner_payout_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    op.execute(
        sa.text(
            "UPDATE bookings SET commission_amount = ROUND(deposit_amount * 0.10, 2), "
            "owner_payout_amount = deposit_amount - ROUND(deposit_amount * 0.10, 2)"
        )
    )
    op.alter_column("bookings", "commission_amount", server_default=None)
    op.alter_column("bookings", "owner_payout_amount", server_default=None)

    op.add_column("payments", sa.Column("merchant_request_id", sa.String(128), nullable=True))
    op.add_column("payments", sa.Column("mpesa_phone", sa.String(12), nullable=True))
    op.add_column("payments", sa.Column("callback_amount", sa.Numeric(10, 2), nullable=True))
    op.add_column("payments", sa.Column("callback_receipt", sa.String(64), nullable=True))
    op.add_column("payments", sa.Column("callback_phone", sa.String(12), nullable=True))
    op.add_column("payments", sa.Column("result_description", sa.Text(), nullable=True))
    op.add_column("payments", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "payments",
        sa.Column("payout_status", sa.String(16), nullable=False, server_default="not_due"),
    )
    op.execute(
        sa.text(
            "UPDATE payments SET payout_status = 'awaiting' "
            "WHERE status = 'completed'"
        )
    )
    op.create_index(
        "uq_payments_checkout_request_id",
        "payments",
        ["checkout_request_id"],
        unique=True,
    )
    op.create_index(
        "uq_payments_active_booking",
        "payments",
        ["booking_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'completed')"),
        sqlite_where=sa.text("status IN ('pending', 'completed')"),
    )


def downgrade() -> None:
    op.drop_index("uq_payments_active_booking", table_name="payments")
    op.drop_index("uq_payments_checkout_request_id", table_name="payments")
    op.drop_column("payments", "payout_status")
    op.drop_column("payments", "paid_at")
    op.drop_column("payments", "result_description")
    op.drop_column("payments", "callback_phone")
    op.drop_column("payments", "callback_receipt")
    op.drop_column("payments", "callback_amount")
    op.drop_column("payments", "mpesa_phone")
    op.drop_column("payments", "merchant_request_id")
    op.drop_column("bookings", "owner_payout_amount")
    op.drop_column("bookings", "commission_amount")
