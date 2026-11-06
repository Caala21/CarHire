import hashlib
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest
from pydantic import SecretStr

from app.core.config import settings
from app.core.database import get_db
from app.models import PasswordResetRequestLog, PasswordResetToken, User
from app.services.auth import hash_password
from app.services.password_reset_senders import (
    ConsolePasswordResetSender,
    SMTPPasswordResetSender,
)


def register_user(client, email="reset@example.com"):
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Amina Wanjiku",
            "email": email,
            "phone": "254712345678",
            "password": "Original-password-1",
        },
    )
    assert response.status_code == 201


def request_reset_token(client, capsys, email="reset@example.com"):
    response = client.post("/api/auth/forgot-password", json={"email": email})
    assert response.status_code == 202
    output = capsys.readouterr().out
    match = re.search(r"^\[DEV PASSWORD RESET\] user=\d+ link=(\S+)$", output, re.MULTILINE)
    assert match is not None
    return parse_qs(urlparse(match.group(1)).query)["token"][0], output


def test_forgot_password_returns_same_response_for_known_and_unknown_email(client, capsys):
    register_user(client)

    known = client.post(
        "/api/auth/forgot-password",
        json={"email": "reset@example.com"},
    )
    known_output = capsys.readouterr().out
    unknown = client.post(
        "/api/auth/forgot-password",
        json={"email": "unknown@example.com"},
    )

    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json() == {
        "message": "If an account exists for that email, a password reset link will be sent."
    }
    assert "[DEV PASSWORD RESET]" in known_output
    assert capsys.readouterr().out == ""


def test_reset_request_stores_only_hash_and_expires_in_30_minutes(
    client, capsys, monkeypatch
):
    register_user(client)
    monkeypatch.setattr(settings, "frontend_url", "https://frontend.example/")

    token, output = request_reset_token(client, capsys)
    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        record = db.query(PasswordResetToken).one()
        assert record.token_hash == hashlib.sha256(token.encode()).hexdigest()
        assert record.token_hash != token
        lifetime = record.expires_at - record.created_at
        assert timedelta(minutes=29, seconds=59) <= lifetime <= timedelta(minutes=30, seconds=1)
        assert db.query(PasswordResetRequestLog).one().email_hash != "reset@example.com"
    finally:
        db_generator.close()

    assert "https://frontend.example/reset-password?token=" in output


def test_reset_password_changes_password_and_rejects_reuse(client, capsys):
    register_user(client)
    token, _ = request_reset_token(client, capsys)

    response = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "New-password-123"},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Password reset successfully"}
    assert client.post(
        "/api/auth/login",
        json={"email": "reset@example.com", "password": "Original-password-1"},
    ).status_code == 401
    assert client.post(
        "/api/auth/login",
        json={"email": "reset@example.com", "password": "New-password-123"},
    ).status_code == 200

    reused = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "Another-password-2"},
    )
    assert reused.status_code == 400
    assert reused.json()["error"]["code"] == "invalid_password_reset_token"
    assert "expired, or already used" in reused.json()["error"]["message"]


def test_expired_and_invalid_reset_tokens_are_rejected(client, capsys):
    register_user(client)
    token, _ = request_reset_token(client, capsys)
    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        record = db.query(PasswordResetToken).one()
        record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    finally:
        db_generator.close()

    expired = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "New-password-123"},
    )
    invalid = client.post(
        "/api/auth/reset-password",
        json={"token": "not-a-valid-token", "new_password": "New-password-123"},
    )
    assert expired.status_code == invalid.status_code == 400
    assert expired.json()["error"]["message"] == invalid.json()["error"]["message"]


def test_new_reset_request_invalidates_previous_token(client, capsys):
    register_user(client)
    old_token, _ = request_reset_token(client, capsys)
    new_token, _ = request_reset_token(client, capsys)

    old = client.post(
        "/api/auth/reset-password",
        json={"token": old_token, "new_password": "Old-token-password"},
    )
    current = client.post(
        "/api/auth/reset-password",
        json={"token": new_token, "new_password": "Current-password"},
    )
    assert old.status_code == 400
    assert current.status_code == 200


def test_google_only_user_can_set_a_password_with_reset_link(client, capsys):
    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        db.add(
            User(
                full_name="Google User",
                email="google@example.com",
                phone=None,
                password_hash=hash_password("random-google-only-password"),
                email_verified_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
    finally:
        db_generator.close()

    token, _ = request_reset_token(client, capsys, "google@example.com")
    response = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "Google-new-password"},
    )

    assert response.status_code == 200
    login = client.post(
        "/api/auth/login",
        json={"email": "google@example.com", "password": "Google-new-password"},
    )
    assert login.status_code == 200


def test_forgot_password_rate_limits_per_email_and_per_ip(client):
    for _ in range(3):
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": "same@example.com"},
        )
        assert response.status_code == 202
    limited_email = client.post(
        "/api/auth/forgot-password",
        json={"email": "same@example.com"},
    )
    assert limited_email.status_code == 429
    assert limited_email.json()["error"]["code"] == "password_reset_rate_limited"

    another_client = client.__class__(client.app, client=("192.0.2.1", 12345))
    for index in range(3):
        response = another_client.post(
            "/api/auth/forgot-password",
            json={"email": f"ip-limit-{index}@example.com"},
        )
        assert response.status_code == 202
    limited_ip = another_client.post(
        "/api/auth/forgot-password",
        json={"email": "fourth-ip-request@example.com"},
    )
    assert limited_ip.status_code == 429


def test_reset_password_requires_at_least_eight_characters(client):
    response = client.post(
        "/api/auth/reset-password",
        json={"token": "token", "new_password": "short"},
    )
    assert response.status_code == 422


def test_reset_password_supports_passwords_longer_than_bcrypt_limit(client, capsys):
    register_user(client)
    token, _ = request_reset_token(client, capsys)
    password = "long-password-" * 8
    response = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": password},
    )

    assert response.status_code == 200
    login = client.post(
        "/api/auth/login",
        json={"email": "reset@example.com", "password": password},
    )
    assert login.status_code == 200


def test_console_reset_sender_never_prints_link_in_production(
    monkeypatch, capsys
):
    monkeypatch.setattr(settings, "production", True)

    with pytest.raises(RuntimeError, match="disabled in production"):
        ConsolePasswordResetSender(42).send(
            "person@example.com",
            "https://frontend.example/reset-password?token=secret",
        )

    assert capsys.readouterr().out == ""


def test_smtp_password_reset_sender_uses_configured_settings(monkeypatch):
    sent_messages = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            assert (host, port, timeout) == ("smtp.example.com", 587, 10)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def starttls(self):
            pass

        def login(self, username, password):
            assert (username, password) == ("smtp-user", "smtp-password")

        def send_message(self, message):
            sent_messages.append(message)

    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_from_email", "noreply@example.com")
    monkeypatch.setattr(settings, "smtp_username", "smtp-user")
    monkeypatch.setattr(settings, "smtp_password", SecretStr("smtp-password"))
    monkeypatch.setattr(settings, "smtp_starttls", True)
    monkeypatch.setattr(
        "app.services.password_reset_senders.smtplib.SMTP",
        FakeSMTP,
    )

    SMTPPasswordResetSender().send(
        "person@example.com",
        "https://frontend.example/reset-password?token=secret",
    )

    assert sent_messages[0]["To"] == "person@example.com"
    assert "expires in 30 minutes" in sent_messages[0].get_content()
    assert "token=secret" in sent_messages[0].get_content()
