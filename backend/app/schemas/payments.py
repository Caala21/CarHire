from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.enums import PaymentMethod, PaymentStatus, PaymentType


class DepositPaymentRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_kenyan_phone(cls, value: str) -> str:
        if (
            len(value) != 12
            or not value.startswith("254")
            or value[3] not in "17"
            or not value[3:].isdigit()
        ):
            raise ValueError("Phone must use Kenyan international format, for example 254712345678")
        return value


class PaymentResponse(BaseModel):
    id: int
    booking_id: int
    amount: Decimal
    type: PaymentType
    method: PaymentMethod
    status: PaymentStatus
    mpesa_receipt: str | None
    paid_at: datetime | None
    result_description: str | None
    payout_status: str

    model_config = ConfigDict(from_attributes=True)


class BookingReceiptResponse(BaseModel):
    booking_id: int
    vehicle: str
    start_date: date
    end_date: date
    amount: Decimal
    mpesa_receipt: str
    paid_at: datetime


class AdminPaymentResponse(BaseModel):
    id: int
    booking_id: int
    vehicle: str
    amount: Decimal
    mpesa_receipt: str | None
    status: PaymentStatus
    payout_status: str
    owner_payout_amount: Decimal
    commission_amount: Decimal
    created_at: datetime


class PayoutPaymentResponse(AdminPaymentResponse):
    owner_id: int | None
    owner_name: str | None
