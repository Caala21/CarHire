import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.models import User, VerificationChannel, VerificationCode
from app.services.verification_senders import send_verification_code

CODE_LIFETIME = timedelta(minutes=10)
RATE_LIMIT_WINDOW = timedelta(hours=1)
MAX_ATTEMPTS = 5
MAX_REQUESTS_PER_HOUR = 3


def _hash_code(user_id: int, channel: VerificationChannel, code: str) -> str:
    payload = f"{user_id}:{channel.value}:{code}".encode()
    return hmac.new(
        settings.jwt_secret_key.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()


def request_verification(
    db: Session, user: User, channel: VerificationChannel
) -> datetime:
    verified_at = (
        user.email_verified_at
        if channel is VerificationChannel.EMAIL
        else user.phone_verified_at
    )
    if verified_at is not None:
        raise AppError(409, "already_verified", f"{channel.value.capitalize()} is already verified")

    now = datetime.now(timezone.utc)
    db.scalar(select(User.id).where(User.id == user.id).with_for_update())
    recent_requests = db.scalar(
        select(func.count(VerificationCode.id)).where(
            VerificationCode.user_id == user.id,
            VerificationCode.created_at >= now - RATE_LIMIT_WINDOW,
        )
    )
    if recent_requests is not None and recent_requests >= MAX_REQUESTS_PER_HOUR:
        raise AppError(
            429,
            "verification_rate_limited",
            "Too many verification requests; try again later",
        )

    previous_codes = db.scalars(
        select(VerificationCode)
        .where(
            VerificationCode.user_id == user.id,
            VerificationCode.channel == channel,
            VerificationCode.used_at.is_(None),
        )
        .with_for_update()
    ).all()
    for previous_code in previous_codes:
        previous_code.used_at = now

    code = f"{secrets.randbelow(1_000_000):06d}"
    record = VerificationCode(
        user_id=user.id,
        channel=channel,
        code_hash=_hash_code(user.id, channel, code),
        expires_at=now + CODE_LIFETIME,
        attempts=0,
    )
    db.add(record)
    db.flush()

    destination = (
        user.email if channel is VerificationChannel.EMAIL else user.phone
    )
    send_verification_code(channel, destination, code, user.id)
    db.commit()
    return record.expires_at


def confirm_verification(
    db: Session, user: User, channel: VerificationChannel, code: str
) -> datetime:
    now = datetime.now(timezone.utc)
    record = db.scalar(
        select(VerificationCode)
        .where(
            VerificationCode.user_id == user.id,
            VerificationCode.channel == channel,
            VerificationCode.used_at.is_(None),
            VerificationCode.expires_at > now,
            VerificationCode.attempts < MAX_ATTEMPTS,
        )
        .order_by(VerificationCode.created_at.desc(), VerificationCode.id.desc())
        .limit(1)
        .with_for_update()
    )
    if record is None:
        raise AppError(400, "invalid_verification_code", "Verification code is invalid or expired")

    expected_hash = _hash_code(user.id, channel, code)
    if not hmac.compare_digest(record.code_hash, expected_hash):
        record.attempts += 1
        if record.attempts >= MAX_ATTEMPTS:
            record.used_at = now
        db.commit()
        raise AppError(400, "invalid_verification_code", "Verification code is invalid or expired")

    if channel is VerificationChannel.EMAIL:
        user.email_verified_at = now
    else:
        user.phone_verified_at = now
    record.used_at = now
    db.commit()
    return now
