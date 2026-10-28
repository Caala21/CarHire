from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import (
    OwnerVerificationStatus,
    VehicleApprovalStatus,
    VehicleStatus,
)


class OwnerApplicationRequest(BaseModel):
    national_id: str = Field(min_length=5, max_length=32)
    kra_pin: str = Field(min_length=5, max_length=16)
    payout_phone: str = Field(pattern=r"^254[17]\d{8}$")


class OwnerApplicationResponse(BaseModel):
    verification_status: OwnerVerificationStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OwnerReviewResponse(BaseModel):
    user_id: int
    full_name: str
    email: str
    phone: str
    verification_status: OwnerVerificationStatus
    rejection_reason: str | None
    reviewed_at: datetime | None
    created_at: datetime
    id_document_download_url: str | None
    selfie_document_download_url: str | None


class RejectionRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("reason")
    @classmethod
    def reject_blank_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Reason cannot be blank")
        return value.strip()


class VehicleCreateRequest(BaseModel):
    make: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=80)
    year: int = Field(ge=1886, le=2100)
    plate: str = Field(min_length=1, max_length=16)
    chassis_number: str = Field(min_length=1, max_length=64)
    seats: int = Field(ge=1, le=100)
    transmission: str = Field(min_length=1, max_length=32)
    fuel_type: str = Field(min_length=1, max_length=32)
    daily_rate: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    deposit_amount: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    insurance_expiry: date
    inspection_expiry: date
    location: str = Field(min_length=1, max_length=500)


class VehiclePatchRequest(BaseModel):
    make: str | None = Field(default=None, min_length=1, max_length=80)
    model: str | None = Field(default=None, min_length=1, max_length=80)
    year: int | None = Field(default=None, ge=1886, le=2100)
    plate: str | None = Field(default=None, min_length=1, max_length=16)
    chassis_number: str | None = Field(default=None, min_length=1, max_length=64)
    seats: int | None = Field(default=None, ge=1, le=100)
    transmission: str | None = Field(default=None, min_length=1, max_length=32)
    fuel_type: str | None = Field(default=None, min_length=1, max_length=32)
    daily_rate: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    deposit_amount: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    insurance_expiry: date | None = None
    inspection_expiry: date | None = None
    location: str | None = Field(default=None, max_length=500)
    status: VehicleStatus | None = None

    model_config = ConfigDict(extra="forbid")


class VehicleResponse(BaseModel):
    id: int
    make: str
    model: str
    year: int
    plate: str
    chassis_number: str | None
    seats: int
    transmission: str
    fuel_type: str
    daily_rate: Decimal
    deposit_amount: Decimal
    status: VehicleStatus
    approval_status: VehicleApprovalStatus
    insurance_expiry: date | None
    inspection_expiry: date | None
    location: str | None
    photos: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VehiclePageResponse(BaseModel):
    items: list[VehicleResponse]
    total: int
    limit: int
    offset: int


class AdminVehicleResponse(VehicleResponse):
    logbook_download_url: str | None
    insurance_download_url: str | None


class FileUploadResponse(BaseModel):
    file_id: int
    download_url: str
