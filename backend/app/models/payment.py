from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import PaymentMethod, PaymentStatus, PaymentType


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    type: Mapped[PaymentType] = mapped_column(
        Enum(PaymentType, name="payment_type", native_enum=False, values_callable=lambda enum: [item.value for item in enum])
    )
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method", native_enum=False, values_callable=lambda enum: [item.value for item in enum])
    )
    mpesa_receipt: Mapped[str | None] = mapped_column(String(64))
    checkout_request_id: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", native_enum=False, values_callable=lambda enum: [item.value for item in enum]),
        default=PaymentStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())