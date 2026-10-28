from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import VehicleApprovalStatus, VehicleStatus


class Vehicle(Base):
    __tablename__ = "vehicles"
    __table_args__ = (UniqueConstraint("chassis_number", name="uq_vehicles_chassis_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL", name="fk_vehicles_owner_id_users"),
        index=True,
    )
    make: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(80))
    year: Mapped[int] = mapped_column(Integer)
    plate: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    chassis_number: Mapped[str | None] = mapped_column(String(64))
    logbook_url: Mapped[str | None] = mapped_column(String(2048))
    insurance_url: Mapped[str | None] = mapped_column(String(2048))
    insurance_expiry: Mapped[date | None] = mapped_column(Date)
    inspection_expiry: Mapped[date | None] = mapped_column(Date)
    approval_status: Mapped[VehicleApprovalStatus] = mapped_column(
        Enum(
            VehicleApprovalStatus,
            name="vehicle_approval_status",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=VehicleApprovalStatus.APPROVED,
        server_default=VehicleApprovalStatus.APPROVED.value,
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(1000))
    location: Mapped[str | None] = mapped_column(Text)
    seats: Mapped[int] = mapped_column(Integer)
    transmission: Mapped[str] = mapped_column(String(32))
    fuel_type: Mapped[str] = mapped_column(String(32))
    daily_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[VehicleStatus] = mapped_column(
        Enum(
            VehicleStatus,
            name="vehicle_status",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=VehicleStatus.AVAILABLE,
    )
    photos: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())