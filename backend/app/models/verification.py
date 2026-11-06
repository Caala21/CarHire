from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import VerificationChannel


class VerificationCode(Base):
    __tablename__ = "verification_codes"
    __table_args__ = (
        Index(
            "ix_verification_codes_user_channel_created",
            "user_id",
            "channel",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    channel: Mapped[VerificationChannel] = mapped_column(
        Enum(
            VerificationChannel,
            name="verification_channel",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        )
    )
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        Index("ix_password_reset_tokens_token_hash", "token_hash", unique=True),
        Index("ix_password_reset_tokens_user_used", "user_id", "used_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PasswordResetRequestLog(Base):
    __tablename__ = "password_reset_request_logs"
    __table_args__ = (
        Index(
            "ix_password_reset_request_logs_email_created",
            "email_hash",
            "created_at",
        ),
        Index(
            "ix_password_reset_request_logs_ip_created",
            "ip_hash",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email_hash: Mapped[str] = mapped_column(String(64))
    ip_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
