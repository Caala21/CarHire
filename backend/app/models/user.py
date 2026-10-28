from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import OwnerVerificationStatus, Role


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(12))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="user_role", native_enum=False, values_callable=lambda enum: [item.value for item in enum]),
        default=Role.CUSTOMER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    profile: Mapped["CustomerProfile | None"] = relationship(back_populates="user", uselist=False)
    owner_profile: Mapped["OwnerProfile | None"] = relationship(
        back_populates="user",
        uselist=False,
        foreign_keys="OwnerProfile.user_id",
    )


class CustomerProfile(Base):
    __tablename__ = "customer_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    national_id: Mapped[str | None] = mapped_column(String(32), unique=True)
    licence_number: Mapped[str | None] = mapped_column(String(64), unique=True)
    licence_expiry: Mapped[date | None] = mapped_column(Date)
    id_doc_url: Mapped[str | None] = mapped_column(String(2048))
    licence_doc_url: Mapped[str | None] = mapped_column(String(2048))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    user: Mapped[User] = relationship(back_populates="profile")


class OwnerProfile(Base):
    __tablename__ = "owner_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    national_id: Mapped[str] = mapped_column(String(32), unique=True)
    kra_pin: Mapped[str] = mapped_column(String(16), unique=True)
    id_doc_url: Mapped[str | None] = mapped_column(String(2048))
    selfie_url: Mapped[str | None] = mapped_column(String(2048))
    payout_phone: Mapped[str] = mapped_column(String(12))
    verification_status: Mapped[OwnerVerificationStatus] = mapped_column(
        Enum(
            OwnerVerificationStatus,
            name="owner_verification_status",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=OwnerVerificationStatus.PENDING,
        server_default=OwnerVerificationStatus.PENDING.value,
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(1000))
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user: Mapped[User] = relationship(back_populates="owner_profile", foreign_keys=[user_id])