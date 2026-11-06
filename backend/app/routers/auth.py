from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.models import User
from app.schemas.auth import (
    LoginRequest,
    ForgotPasswordRequest,
    GoogleLoginRequest,
    PhoneUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    VerificationConfirmRequest,
    VerificationRequest,
    VerificationResponse,
)
from app.services.auth import (
    authenticate_google_user,
    authenticate_user,
    create_token,
    decode_token,
    register_user,
    update_user_phone,
)
from app.services.verification import confirm_verification, request_verification
from app.services.password_reset import (
    GENERIC_REQUEST_MESSAGE,
    request_password_reset,
    reset_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_token(token, "access")
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AppError(401, "invalid_token", "Token subject is invalid") from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError(401, "invalid_token", "User is unavailable")
    return user


def require_role(*roles: str):
    def guard(user: User = Depends(current_user)) -> User:
        if user.role.value not in roles:
            raise AppError(403, "forbidden", "You do not have permission to access this resource")
        return user

    return guard


def require_verified_phone(user: User = Depends(current_user)) -> User:
    if user.phone_verified_at is None:
        raise AppError(403, "phone_not_verified", "Phone verification is required")
    return user


def token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_token(user, "access"),
        refresh_token=create_token(user, "refresh"),
        user=UserResponse.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return token_response(register_user(db, payload))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return token_response(authenticate_user(db, str(payload.email), payload.password))


@router.post("/forgot-password", response_model=VerificationResponse, status_code=202)
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> VerificationResponse:
    client_ip = request.client.host if request.client is not None else "unknown"
    request_password_reset(db, str(payload.email), client_ip)
    return VerificationResponse(message=GENERIC_REQUEST_MESSAGE)


@router.post("/reset-password", response_model=VerificationResponse)
def reset_password_endpoint(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> VerificationResponse:
    reset_password(db, payload)
    return VerificationResponse(message="Password reset successfully")


@router.post("/google", response_model=TokenResponse)
def google_login(payload: GoogleLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return token_response(authenticate_google_user(db, payload.credential))


@router.post("/phone", response_model=UserResponse)
def update_phone(
    payload: PhoneUpdateRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    return UserResponse.model_validate(update_user_phone(db, user, payload.phone))


@router.post("/token", response_model=TokenResponse)
def token(
    payload: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    return token_response(authenticate_user(db, payload.username, payload.password))


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    claims = decode_token(payload.refresh_token, "refresh")
    try:
        user_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AppError(401, "invalid_token", "Token subject is invalid") from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError(401, "invalid_token", "User is unavailable")
    return token_response(user)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(current_user)) -> User:
    return user


@router.post(
    "/verify/request",
    response_model=VerificationResponse,
    status_code=202,
)
def request_verification_code(
    payload: VerificationRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> VerificationResponse:
    request_verification(db, user, payload.channel)
    return VerificationResponse(message="Verification code sent")


@router.post("/verify/confirm", response_model=VerificationResponse)
def confirm_verification_code(
    payload: VerificationConfirmRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> VerificationResponse:
    confirm_verification(db, user, payload.channel, payload.code)
    return VerificationResponse(message=f"{payload.channel.value.capitalize()} verified")