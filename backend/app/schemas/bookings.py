from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import BookingStatus


class BookingCreateRequest(BaseModel):
    vehicle_id: int = Field(gt=0)
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_date_range(self) -> "BookingCreateRequest":
        if self.start_date < date.today():
            raise ValueError("start_date cannot be in the past")
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class BookingVehicleResponse(BaseModel):
    id: int
    make: str
    model: str
    year: int
    photos: list[str]

    model_config = ConfigDict(from_attributes=True)


class BookingResponse(BaseModel):
    id: int
    customer_id: int
    vehicle_id: int
    vehicle: BookingVehicleResponse
    start_date: date
    end_date: date
    status: BookingStatus
    total_price: Decimal
    deposit_amount: Decimal
    deposit_paid: bool
    expires_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AvailabilityRange(BaseModel):
    start_date: date
    end_date: date


class AvailabilityResponse(BaseModel):
    vehicle_id: int
    blocked_ranges: list[AvailabilityRange]


class VehicleBlockCreateRequest(BaseModel):
    start_date: date
    end_date: date
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_date_range(self) -> "VehicleBlockCreateRequest":
        if self.start_date < date.today():
            raise ValueError("start_date cannot be in the past")
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class VehicleBlockResponse(BaseModel):
    id: int
    vehicle_id: int
    start_date: date
    end_date: date
    reason: str | None
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
