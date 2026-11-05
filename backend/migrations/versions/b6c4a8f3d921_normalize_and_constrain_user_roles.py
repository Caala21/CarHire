"""Normalize and constrain user roles

Revision ID: b6c4a8f3d921
Revises: 91f45a5cb67d
Create Date: 2026-11-05 20:14:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b6c4a8f3d921"
down_revision: Union[str, None] = "91f45a5cb67d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("UPDATE users SET role = lower(role)"))
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('customer', 'staff', 'admin', 'owner')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
