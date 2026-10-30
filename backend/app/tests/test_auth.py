from app.core.database import get_db
from app.models import Role, User


def registration_payload():
    return {
        "full_name": "Amina Wanjiku",
        "email": "amina@example.com",
        "phone": "254712345678",
        "password": "CorrectHorseBattery9",
    }


def test_register_creates_customer_and_returns_tokens(client):
    response = client.post("/api/auth/register", json=registration_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["role"] == "customer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert "password_hash" not in body["user"]


def test_login_returns_tokens(client):
    client.post("/api/auth/register", json=registration_payload())

    response = client.post(
        "/api/auth/login",
        json={"email": "amina@example.com", "password": "CorrectHorseBattery9"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "amina@example.com"


def test_google_token_verification_uses_configured_client_id(monkeypatch):
    from app.services import google_auth

    monkeypatch.setattr(google_auth.settings, "google_client_id", "configured-client-id")

    def verify(credential, request, audience):
        assert credential == "credential"
        assert audience == "configured-client-id"
        return {"email": "verified@example.com"}

    monkeypatch.setattr(google_auth.id_token, "verify_oauth2_token", verify)

    assert google_auth.verify_google_token("credential") == {"email": "verified@example.com"}


def test_google_login_creates_verified_customer_with_unusable_password(client, monkeypatch):
    claims = {
        "email": "new.google@example.com",
        "email_verified": True,
        "name": "Google Customer",
        "role": "admin",
    }

    def verify(credential):
        assert credential == "mocked-google-credential"
        return claims

    monkeypatch.setattr("app.services.google_auth.verify_google_token", verify)
    response = client.post(
        "/api/auth/google",
        json={"credential": "mocked-google-credential"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["email"] == "new.google@example.com"
    assert body["user"]["full_name"] == "Google Customer"
    assert body["user"]["role"] == "customer"
    assert body["user"]["email_verified_at"]
    assert body["user"]["phone"] is None
    assert "password_hash" not in body["user"]


def test_google_login_uses_existing_user_by_email(client, monkeypatch):
    registered = client.post("/api/auth/register", json=registration_payload()).json()
    monkeypatch.setattr(
        "app.services.google_auth.verify_google_token",
        lambda credential: {
            "email": "AMINA@example.com",
            "email_verified": True,
            "name": "A Different Name",
            "role": "admin",
        },
    )

    response = client.post("/api/auth/google", json={"credential": "mocked"})

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["id"] == registered["user"]["id"]
    assert body["user"]["role"] == "customer"
    assert body["user"]["full_name"] == "Amina Wanjiku"
    assert body["user"]["email_verified_at"]


def test_google_login_rejects_unverified_email(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.google_auth.verify_google_token",
        lambda credential: {
            "email": "unverified@example.com",
            "email_verified": False,
            "name": "Unverified User",
        },
    )

    response = client.post("/api/auth/google", json={"credential": "mocked"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_google_token"


def test_google_account_can_set_phone_before_verification(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.google_auth.verify_google_token",
        lambda credential: {
            "email": "phone@example.com",
            "email_verified": True,
            "name": "Phone User",
        },
    )
    tokens = client.post("/api/auth/google", json={"credential": "mocked"}).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    missing_phone = client.post(
        "/api/auth/verify/request",
        json={"channel": "phone"},
        headers=headers,
    )
    updated = client.post(
        "/api/auth/phone",
        json={"phone": "254712345678"},
        headers=headers,
    )
    requested = client.post(
        "/api/auth/verify/request",
        json={"channel": "phone"},
        headers=headers,
    )

    assert missing_phone.status_code == 409
    assert missing_phone.json()["error"]["code"] == "phone_required"
    assert updated.status_code == 200
    assert updated.json()["phone"] == "254712345678"
    assert requested.status_code == 202


def test_oauth_token_accepts_form_credentials(client):
    client.post("/api/auth/register", json=registration_payload())

    openapi = client.get("/openapi.json").json()
    assert client.get("/docs").status_code == 200
    assert all(path.startswith("/api/") for path in openapi["paths"])
    response = client.post(
        "/api/auth/token",
        data={
            "username": "amina@example.com",
            "password": "CorrectHorseBattery9",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "amina@example.com"
    assert body["access_token"]
    assert body["refresh_token"]
    assert (
        openapi["components"]["securitySchemes"]["OAuth2PasswordBearer"]["flows"]["password"]["tokenUrl"]
        == "/api/auth/token"
    )


def test_refresh_rotates_tokens_and_me_returns_user(client):
    registered = client.post("/api/auth/register", json=registration_payload()).json()

    refreshed = client.post("/api/auth/refresh", json={"refresh_token": registered["refresh_token"]})
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {refreshed.json()['access_token']}"})

    assert refreshed.status_code == 200
    assert me.status_code == 200
    assert me.json()["email"] == "amina@example.com"


def test_non_admin_is_blocked_from_admin_route(client):
    registered = client.post("/api/auth/register", json=registration_payload()).json()

    response = client.get("/api/admin/ping", headers={"Authorization": f"Bearer {registered['access_token']}"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_admin_can_access_admin_route(client, admin_user):
    def override_get_db():
        from app.core.database import SessionLocal

        with SessionLocal() as session:
            yield session

    # Use the test database session from the active dependency override.
    original = client.app.dependency_overrides[get_db]

    def seed_admin():
        generator = original()
        session = next(generator)
        session.add(admin_user)
        session.commit()
        try:
            yield session
        finally:
            generator.close()

    client.app.dependency_overrides[get_db] = seed_admin
    login = client.post("/api/auth/login", json={"email": admin_user.email, "password": "Admin-password-123"})
    client.app.dependency_overrides[get_db] = original

    response = client.get("/api/admin/ping", headers={"Authorization": f"Bearer {login.json()['access_token']}"})

    assert response.status_code == 200