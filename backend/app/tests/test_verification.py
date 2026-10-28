import re
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import SecretStr

from app.core.config import Settings, settings
from app.core.database import get_db
from app.core.errors import AppError
from app.models import User, VerificationChannel, VerificationCode
from app.services.verification_senders import (
    AfricasTalkingSMSVerificationSender,
    ConsoleVerificationSender,
    SMTPEmailVerificationSender,
)


def register_and_authenticate(client):
    registration = client.post(
        "/auth/register",
        json={
            "full_name": "Amina Wanjiku",
            "email": "amina@example.com",
            "phone": "254712345678",
            "password": "CorrectHorseBattery9",
        },
    )
    assert registration.status_code == 201
    return {"Authorization": f"Bearer {registration.json()['access_token']}"}


def last_printed_code(capsys):
    output = capsys.readouterr().out
    match = re.search(
        r"^\[DEV VERIFICATION\] channel=(?:email|phone) user=\d+ code=(\d{6})$",
        output,
        re.MULTILINE,
    )
    assert match is not None
    return match.group(1)


def test_verification_endpoints_require_login(client):
    assert client.post("/auth/verify/request", json={"channel": "email"}).status_code == 401
    assert (
        client.post(
            "/auth/verify/confirm",
            json={"channel": "email", "code": "123456"},
        ).status_code
        == 401
    )


@pytest.mark.parametrize(
    ("channel", "verified_field"),
    [
        ("email", "email_verified_at"),
        ("phone", "phone_verified_at"),
    ],
)
def test_verification_request_and_confirm(client, capsys, channel, verified_field):
    headers = register_and_authenticate(client)

    response = client.post(
        "/auth/verify/request",
        json={"channel": channel},
        headers=headers,
    )

    assert response.status_code == 202
    assert response.json() == {"message": "Verification code sent"}
    console_output = capsys.readouterr().out
    match = re.search(
        rf"^\[DEV VERIFICATION\] channel={channel} user=1 code=(\d{{6}})$",
        console_output,
        re.MULTILINE,
    )
    assert match is not None
    code = match.group(1)

    confirm = client.post(
        "/auth/verify/confirm",
        json={"channel": channel, "code": code},
        headers=headers,
    )

    assert confirm.status_code == 200
    profile = client.get("/auth/me", headers=headers).json()
    assert profile[verified_field] is not None
    other_field = "phone_verified_at" if channel == "email" else "email_verified_at"
    assert profile[other_field] is None
    assert code not in confirm.text

    reused = client.post(
        "/auth/verify/confirm",
        json={"channel": channel, "code": code},
        headers=headers,
    )
    assert reused.status_code == 400


def test_verification_code_is_stored_as_a_hash(client, capsys):
    headers = register_and_authenticate(client)
    client.post("/auth/verify/request", json={"channel": "email"}, headers=headers)
    code = last_printed_code(capsys)

    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        record = db.query(VerificationCode).one()
        assert record.code_hash != code
        assert len(record.code_hash) == 64
        assert record.attempts == 0
        lifetime = record.expires_at - record.created_at
        assert timedelta(minutes=9, seconds=59) <= lifetime <= timedelta(minutes=10, seconds=1)
    finally:
        db_generator.close()


def test_wrong_code_is_limited_to_five_attempts(client, capsys):
    headers = register_and_authenticate(client)
    client.post("/auth/verify/request", json={"channel": "email"}, headers=headers)
    code = last_printed_code(capsys)
    wrong_code = f"{(int(code) + 1) % 1_000_000:06d}"

    for _ in range(5):
        response = client.post(
            "/auth/verify/confirm",
            json={"channel": "email", "code": wrong_code},
            headers=headers,
        )
        assert response.status_code == 400

    blocked = client.post(
        "/auth/verify/confirm",
        json={"channel": "email", "code": code},
        headers=headers,
    )
    assert blocked.status_code == 400

    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        record = db.query(VerificationCode).one()
        assert record.attempts == 5
        assert record.used_at is not None
    finally:
        db_generator.close()


def test_verification_code_expires(client, capsys):
    headers = register_and_authenticate(client)
    client.post("/auth/verify/request", json={"channel": "email"}, headers=headers)
    code = last_printed_code(capsys)

    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        record = db.query(VerificationCode).one()
        record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    finally:
        db_generator.close()

    response = client.post(
        "/auth/verify/confirm",
        json={"channel": "email", "code": code},
        headers=headers,
    )
    assert response.status_code == 400


def test_resend_limit_is_three_per_user_across_channels(client, capsys):
    headers = register_and_authenticate(client)
    for channel in ("email", "phone", "email"):
        response = client.post(
            "/auth/verify/request",
            json={"channel": channel},
            headers=headers,
        )
        assert response.status_code == 202

    limited = client.post(
        "/auth/verify/request",
        json={"channel": "phone"},
        headers=headers,
    )

    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "verification_rate_limited"


def test_console_sender_prints_visible_line_in_development(monkeypatch, capsys):
    monkeypatch.setattr(settings, "production", False)
    ConsoleVerificationSender(
        channel=VerificationChannel.PHONE,
        user_id=42,
    ).send("254712345678", "123456")

    assert capsys.readouterr().out == (
        "[DEV VERIFICATION] channel=phone user=42 code=123456\n"
    )


def test_console_sender_never_prints_code_in_production(monkeypatch, capsys):
    monkeypatch.setattr(settings, "production", True)

    with pytest.raises(RuntimeError, match="disabled in production"):
        ConsoleVerificationSender(
            channel=VerificationChannel.EMAIL,
            user_id=42,
        ).send("person@example.com", "123456")

    assert capsys.readouterr().out == ""


def test_require_verified_phone_dependency():
    from app.routers.auth import require_verified_phone

    with pytest.raises(AppError) as error:
        require_verified_phone(User(phone_verified_at=None))
    assert error.value.code == "phone_not_verified"

    user = User(phone_verified_at=datetime.now(timezone.utc))
    assert require_verified_phone(user) is user


def test_smtp_sender_uses_configured_environment_settings(monkeypatch):
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

        def send_message(self, message):
            sent_messages.append(message)

    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_from_email", "noreply@example.com")
    monkeypatch.setattr(settings, "smtp_starttls", True)
    monkeypatch.setattr("app.services.verification_senders.smtplib.SMTP", FakeSMTP)

    SMTPEmailVerificationSender().send("person@example.com", "123456")

    assert sent_messages[0]["To"] == "person@example.com"
    assert "123456" in sent_messages[0].get_content()


def test_africas_talking_sender_uses_configured_environment_settings(monkeypatch):
    captured = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(settings, "africastalking_username", "sandbox")
    monkeypatch.setattr(
        settings,
        "africastalking_api_key",
        SecretStr("test-api-key"),
    )
    monkeypatch.setattr(settings, "africastalking_sandbox", True)
    monkeypatch.setattr("app.services.verification_senders.urlopen", fake_urlopen)

    AfricasTalkingSMSVerificationSender().send("254712345678", "123456")

    request = captured["request"]
    assert request.full_url == "https://api.sandbox.africastalking.com/version1/messaging"
    assert request.get_header("Apikey") == "test-api-key"
    assert captured["timeout"] == 10
    assert b"123456" in request.data


def test_production_settings_reject_insecure_defaults():
    with pytest.raises(ValueError):
        Settings(_env_file=None, production=True)
