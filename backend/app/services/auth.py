from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import secrets
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.models import Role, User
from app.schemas.auth import RegisterRequest
from app.services import google_auth

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_token(user: User, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    lifetime = (
        timedelta(minutes=settings.access_token_minutes)
        if token_type == "access"
        else timedelta(days=settings.refresh_token_days)
    )
    return jwt.encode(
        {"sub": str(user.id), "role": user.role.value, "type": token_type, "iat": now, "exp": now + lifetime},
        settings.jwt_secret_key,
        algorithm=ALGORITHM,
    )


def decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError as exc:
        raise AppError(401, "invalid_token", "Token is invalid or expired") from exc
    if payload.get("type") != expected_type:
        raise AppError(401, "invalid_token", "Token has the wrong type")
    return payload


def register_user(db: Session, request: RegisterRequest) -> User:
    if db.scalar(select(User).where(User.email == request.email)):
        raise AppError(409, "email_in_use", "An account with this email already exists")
    user = User(
        full_name=request.full_name,
        email=str(request.email).lower(),
        phone=request.phone,
        password_hash=hash_password(request.password),
        role=Role.CUSTOMER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None or not verify_password(password, user.password_hash):
        raise AppError(401, "invalid_credentials", "Email or password is incorrect")
    if not user.is_active:
        raise AppError(403, "account_inactive", "This account is inactive")
    return user


def authenticate_google_user(db: Session, credential: str) -> User:
    claims = google_auth.verify_google_token(credential)
    if claims.get("email_verified") is not True:
        raise AppError(401, "invalid_google_token", "Google account email is not verified")

    email = claims.get("email")
    full_name = claims.get("name")
    if (
        not isinstance(email, str)
        or not email.strip()
        or len(email) > 320
        or "@" not in email
        or not isinstance(full_name, str)
        or not full_name.strip()
        or len(full_name.strip()) > 160
    ):
        raise AppError(401, "invalid_google_token", "Google account details are incomplete")

    normalized_email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None:
        user = User(
            full_name=full_name.strip(),
            email=normalized_email,
            phone=None,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            role=Role.CUSTOMER,
            email_verified_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif not user.is_active:
        raise AppError(403, "account_inactive", "This account is inactive")
    elif user.email_verified_at is None:
        user.email_verified_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)

    return user


def update_user_phone(db: Session, user: User, phone: str) -> User:
    if user.phone_verified_at is not None:
        raise AppError(409, "phone_already_verified", "A verified phone number cannot be changed")
    user.phone = phone
    db.commit()
    db.refresh(user)
    return user