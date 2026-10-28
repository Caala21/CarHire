from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, Integer, JSON, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import VehicleStatus


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    make: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(80))
    year: Mapped[int] = mapped_column(Integer)
    plate: Mapped[str] = mapped_column(String(16), unique=True, index=True)
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