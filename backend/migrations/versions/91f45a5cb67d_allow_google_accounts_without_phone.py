"""Allow Google accounts without a phone number before verification

Revision ID: 91f45a5cb67d
Revises: 4272abf5a5eb
Create Date: 2026-10-30 13:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "91f45a5cb67d"
down_revision: Union[str, None] = "4272abf5a5eb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("users", "phone", existing_type=sa.String(length=12), nullable=True)


def downgrade() -> None:
    op.alter_column("users", "phone", existing_type=sa.String(length=12), nullable=False)
