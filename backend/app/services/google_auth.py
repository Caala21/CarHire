from google.auth.exceptions import GoogleAuthError, TransportError
from google.auth.transport.requests import Request
from google.oauth2 import id_token

from app.core.config import settings
from app.core.errors import AppError


def verify_google_token(credential: str) -> dict:
    if not settings.google_client_id:
        raise AppError(503, "google_sign_in_unavailable", "Google sign-in is not configured")

    try:
        return id_token.verify_oauth2_token(
            credential,
            Request(),
            audience=settings.google_client_id,
        )
    except TransportError as exc:
        raise AppError(503, "google_verification_unavailable", "Google could not be reached to verify the credential") from exc
    except (GoogleAuthError, ValueError) as exc:
        raise AppError(401, "invalid_google_token", "Google credential is invalid or expired") from exc
