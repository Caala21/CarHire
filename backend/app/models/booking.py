from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import BookingStatus


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (Index("ix_bookings_vehicle_dates", "vehicle_id", "start_date", "end_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(
            BookingStatus,
            name="booking_status",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=BookingStatus.PENDING,
    )
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    deposit_paid: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())