"""Add password reset tokens and request rate-limit log

Revision ID: 71b3c9e2a604
Revises: 65c4d9a1f2b7
Create Date: 2026-11-06 12:02:14.615000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "71b3c9e2a604"
down_revision: Union[str, None] = "65c4d9a1f2b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_password_reset_tokens_token_hash",
        "password_reset_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_password_reset_tokens_user_used",
        "password_reset_tokens",
        ["user_id", "used_at"],
        unique=False,
    )
    op.create_table(
        "password_reset_request_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email_hash", sa.String(length=64), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_password_reset_request_logs_email_created",
        "password_reset_request_logs",
        ["email_hash", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_password_reset_request_logs_ip_created",
        "password_reset_request_logs",
        ["ip_hash", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_password_reset_request_logs_ip_created",
        table_name="password_reset_request_logs",
    )
    op.drop_index(
        "ix_password_reset_request_logs_email_created",
        table_name="password_reset_request_logs",
    )
    op.drop_table("password_reset_request_logs")
    op.drop_index("ix_password_reset_tokens_user_used", table_name="password_reset_tokens")
    op.drop_index(
        "ix_password_reset_tokens_token_hash",
        table_name="password_reset_tokens",
    )
    op.drop_table("password_reset_tokens")
