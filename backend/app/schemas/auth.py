from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.enums import VerificationChannel


class UserRole(StrEnum):
    CUSTOMER = "customer"
    STAFF = "staff"
    ADMIN = "admin"
    OWNER = "owner"


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    phone: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("phone")
    @classmethod
    def validate_kenyan_phone(cls, value: str) -> str:
        if len(value) != 12 or not value.startswith("254") or value[3] not in "17" or not value[3:].isdigit():
            raise ValueError("Phone must use Kenyan international format, for example 254712345678")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class GoogleLoginRequest(BaseModel):
    credential: str = Field(min_length=1)


class PhoneUpdateRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_kenyan_phone(cls, value: str) -> str:
        if len(value) != 12 or not value.startswith("254") or value[3] not in "17" or not value[3:].isdigit():
            raise ValueError("Phone must use Kenyan international format, for example 254712345678")
        return value


class RefreshRequest(BaseModel):
    refresh_token: str


class VerificationRequest(BaseModel):
    channel: VerificationChannel


class VerificationConfirmRequest(BaseModel):
    channel: VerificationChannel
    code: str = Field(pattern=r"^\d{6}$")


class VerificationResponse(BaseModel):
    message: str


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone: str | None
    role: UserRole
    is_active: bool
    created_at: datetime
    email_verified_at: datetime | None
    phone_verified_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class BookingDates(BaseModel):
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_date_order(self) -> "BookingDates":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self