from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import PaymentMethod, PaymentStatus, PaymentType


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("uq_payments_checkout_request_id", "checkout_request_id", unique=True),
        Index(
            "uq_payments_active_booking",
            "booking_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'completed')"),
            sqlite_where=text("status IN ('pending', 'completed')"),
        ),
    )

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
    merchant_request_id: Mapped[str | None] = mapped_column(String(128))
    mpesa_phone: Mapped[str | None] = mapped_column(String(12))
    callback_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    callback_receipt: Mapped[str | None] = mapped_column(String(64))
    callback_phone: Mapped[str | None] = mapped_column(String(12))
    result_description: Mapped[str | None] = mapped_column(Text)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payout_status: Mapped[str] = mapped_column(String(16), default="not_due", server_default="not_due")
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", native_enum=False, values_callable=lambda enum: [item.value for item in enum]),
        default=PaymentStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    booking: Mapped["Booking"] = relationship()