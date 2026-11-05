"""Add vehicle pickup locations and reverse-geocode cache

Revision ID: 8baf0d7c3912
Revises: 3ae7c1d9f042
Create Date: 2026-11-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8baf0d7c3912"
down_revision: Union[str, None] = "3ae7c1d9f042"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vehicles", sa.Column("area_name", sa.String(length=160), nullable=True))
    op.add_column("vehicles", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("vehicles", sa.Column("longitude", sa.Float(), nullable=True))
    op.create_check_constraint(
        "ck_vehicles_coordinate_pair",
        "vehicles",
        "(latitude IS NULL AND longitude IS NULL) OR "
        "(latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180)",
    )
    op.create_table(
        "geocode_cache",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("area_name", sa.String(length=160), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "latitude", "longitude", name="uq_geocode_cache_coordinates"
        ),
    )
    op.create_index("ix_geocode_cache_latitude", "geocode_cache", ["latitude"])
    op.create_index("ix_geocode_cache_longitude", "geocode_cache", ["longitude"])


def downgrade() -> None:
    op.drop_index("ix_geocode_cache_longitude", table_name="geocode_cache")
    op.drop_index("ix_geocode_cache_latitude", table_name="geocode_cache")
    op.drop_table("geocode_cache")
    op.drop_constraint("ck_vehicles_coordinate_pair", "vehicles", type_="check")
    op.drop_column("vehicles", "longitude")
    op.drop_column("vehicles", "latitude")
    op.drop_column("vehicles", "area_name")
