from enum import StrEnum


class Role(StrEnum):
    CUSTOMER = "customer"
    STAFF = "staff"
    ADMIN = "admin"


class VehicleStatus(StrEnum):
    AVAILABLE = "available"
    BOOKED = "booked"
    MAINTENANCE = "maintenance"


class BookingStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentType(StrEnum):
    DEPOSIT = "deposit"
    BALANCE = "balance"
    LATE_FEE = "late_fee"


class PaymentMethod(StrEnum):
    MPESA = "mpesa"
    CASH = "cash"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class VerificationChannel(StrEnum):
    EMAIL = "email"
    PHONE = "phone"