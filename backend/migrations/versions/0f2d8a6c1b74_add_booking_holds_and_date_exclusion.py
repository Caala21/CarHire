"""Add booking holds and date exclusion

Revision ID: 0f2d8a6c1b74
Revises: b6c4a8f3d921
Create Date: 2026-11-05 20:17:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0f2d8a6c1b74"
down_revision: Union[str, None] = "b6c4a8f3d921"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("bookings", sa.Column("deposit_amount", sa.Numeric(10, 2), nullable=True))
    op.add_column("bookings", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        sa.text(
            "UPDATE bookings SET deposit_amount = vehicles.deposit_amount "
            "FROM vehicles WHERE bookings.vehicle_id = vehicles.id"
        )
    )
    op.execute(
        sa.text(
            "UPDATE bookings SET expires_at = created_at + interval '30 minutes' "
            "WHERE status = 'pending' AND deposit_paid = false"
        )
    )
    op.alter_column("bookings", "deposit_amount", nullable=False)
    op.create_check_constraint(
        "ck_bookings_dates",
        "bookings",
        "end_date > start_date",
    )
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
    op.execute(
        sa.text(
            "ALTER TABLE bookings ADD CONSTRAINT excl_bookings_active_vehicle_dates "
            "EXCLUDE USING gist (vehicle_id WITH =, "
            "daterange(start_date, end_date, '[)') WITH &&) "
            "WHERE (status IN ('pending', 'confirmed', 'active'))"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE bookings DROP CONSTRAINT excl_bookings_active_vehicle_dates"
        )
    )
    op.drop_constraint("ck_bookings_dates", "bookings", type_="check")
    op.drop_column("bookings", "expires_at")
    op.drop_column("bookings", "deposit_amount")
