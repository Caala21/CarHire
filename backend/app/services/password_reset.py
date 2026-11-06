import hashlib
import hmac
import logging
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.models import PasswordResetRequestLog, PasswordResetToken, User
from app.schemas.auth import ResetPasswordRequest
from app.services.auth import hash_password
from app.services.password_reset_senders import send_password_reset

logger = logging.getLogger(__name__)

TOKEN_LIFETIME = timedelta(minutes=30)
RATE_LIMIT_WINDOW = timedelta(hours=1)
MAX_REQUESTS_PER_HOUR = 3
GENERIC_REQUEST_MESSAGE = (
    "If an account exists for that email, a password reset link will be sent."
)
INVALID_TOKEN_MESSAGE = (
    "This password reset link is invalid, expired, or already used. "
    "Request a new link to reset your password."
)


def _key_hash(value: str, purpose: str) -> str:
    return hmac.new(
        settings.jwt_secret_key.encode(),
        f"password-reset:{purpose}:{value}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def request_password_reset(db: Session, email: str, client_ip: str) -> None:
    normalized_email = email.strip().lower()
    email_hash = _key_hash(normalized_email, "email")
    ip_hash = _key_hash(client_ip, "ip")
    now = datetime.now(timezone.utc)
    window_start = now - RATE_LIMIT_WINDOW

    if db.get_bind().dialect.name == "postgresql":
        lock_keys = sorted(
            {
                int.from_bytes(bytes.fromhex(email_hash[:16]), "big", signed=True),
                int.from_bytes(bytes.fromhex(ip_hash[:16]), "big", signed=True),
            }
        )
        for lock_key in lock_keys:
            db.execute(
                text("SELECT pg_advisory_xact_lock(:lock_key)"),
                {"lock_key": lock_key},
            )

    db.execute(
        delete(PasswordResetRequestLog).where(
            PasswordResetRequestLog.created_at < window_start
        )
    )
    email_requests = db.scalar(
        select(func.count(PasswordResetRequestLog.id)).where(
            PasswordResetRequestLog.email_hash == email_hash,
            PasswordResetRequestLog.created_at >= window_start,
        )
    )
    ip_requests = db.scalar(
        select(func.count(PasswordResetRequestLog.id)).where(
            PasswordResetRequestLog.ip_hash == ip_hash,
            PasswordResetRequestLog.created_at >= window_start,
        )
    )
    if (
        (email_requests is not None and email_requests >= MAX_REQUESTS_PER_HOUR)
        or (ip_requests is not None and ip_requests >= MAX_REQUESTS_PER_HOUR)
    ):
        raise AppError(
            429,
            "password_reset_rate_limited",
            "Too many password reset requests; try again later",
        )

    user = db.scalar(select(User).where(func.lower(User.email) == normalized_email))
    request_log = PasswordResetRequestLog(
        email_hash=email_hash,
        ip_hash=ip_hash,
        created_at=now,
    )
    db.add(request_log)

    if user is None:
        db.commit()
        return

    db.scalar(select(User.id).where(User.id == user.id).with_for_update())
    previous_tokens = db.scalars(
        select(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .with_for_update()
    ).all()
    for previous_token in previous_tokens:
        previous_token.used_at = now

    token = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=_token_hash(token),
            expires_at=now + TOKEN_LIFETIME,
            created_at=now,
        )
    )
    db.commit()

    reset_link = (
        f"{settings.frontend_url.rstrip('/')}/reset-password?"
        f"{urlencode({'token': token})}"
    )
    try:
        send_password_reset(user.email, reset_link, user.id)
    except (OSError, RuntimeError, smtplib.SMTPException):
        logger.exception("Password reset email delivery failed for user_id=%s", user.id)


def reset_password(db: Session, payload: ResetPasswordRequest) -> None:
    now = datetime.now(timezone.utc)
    token_hash = _token_hash(payload.token)
    candidate = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    if candidate is None or not hmac.compare_digest(candidate.token_hash, token_hash):
        raise AppError(400, "invalid_password_reset_token", INVALID_TOKEN_MESSAGE)

    user = db.scalar(
        select(User).where(User.id == candidate.user_id).with_for_update()
    )
    if user is None:
        raise AppError(400, "invalid_password_reset_token", INVALID_TOKEN_MESSAGE)

    record = db.scalar(
        select(PasswordResetToken)
        .where(
            PasswordResetToken.id == candidate.id,
            PasswordResetToken.token_hash == token_hash,
        )
        .with_for_update()
    )
    if (
        record is None
        or not hmac.compare_digest(record.token_hash, token_hash)
        or record.used_at is not None
    ):
        raise AppError(400, "invalid_password_reset_token", INVALID_TOKEN_MESSAGE)

    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise AppError(400, "invalid_password_reset_token", INVALID_TOKEN_MESSAGE)

    user.password_hash = hash_password(payload.new_password)
    record.used_at = now
    db.commit()
