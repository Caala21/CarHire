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
    response = client.post("/auth/register", json=registration_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["role"] == "customer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert "password_hash" not in body["user"]


def test_login_returns_tokens(client):
    client.post("/auth/register", json=registration_payload())

    response = client.post(
        "/auth/login",
        json={"email": "amina@example.com", "password": "CorrectHorseBattery9"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "amina@example.com"


def test_refresh_rotates_tokens_and_me_returns_user(client):
    registered = client.post("/auth/register", json=registration_payload()).json()

    refreshed = client.post("/auth/refresh", json={"refresh_token": registered["refresh_token"]})
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {refreshed.json()['access_token']}"})

    assert refreshed.status_code == 200
    assert me.status_code == 200
    assert me.json()["email"] == "amina@example.com"


def test_non_admin_is_blocked_from_admin_route(client):
    registered = client.post("/auth/register", json=registration_payload()).json()

    response = client.get("/admin/ping", headers={"Authorization": f"Bearer {registered['access_token']}"})

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
    login = client.post("/auth/login", json={"email": admin_user.email, "password": "Admin-password-123"})
    client.app.dependency_overrides[get_db] = original

    response = client.get("/admin/ping", headers={"Authorization": f"Bearer {login.json()['access_token']}"})

    assert response.status_code == 200