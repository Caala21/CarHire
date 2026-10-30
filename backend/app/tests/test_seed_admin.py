from contextlib import contextmanager

import pytest

from app.core.database import get_db
from app.jobs import seed_admin
from app.models import Role, User
from app.services.auth import verify_password


def test_seed_admin_creates_admin_with_hashed_password(client):
    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        user, changed = seed_admin.seed_admin(
            db,
            email="seeded-admin@example.com",
            full_name="Seeded Admin",
            phone="254712345678",
            password="A-secure-admin-password",
        )

        assert changed is True
        assert user.role is Role.ADMIN
        assert user.password_hash != "A-secure-admin-password"
        assert verify_password("A-secure-admin-password", user.password_hash)
    finally:
        generator.close()


def test_seed_admin_requires_explicit_promotion_for_existing_user(client):
    registration = client.post(
        "/api/auth/register",
        json={
            "full_name": "Existing Customer",
            "email": "existing-customer@example.com",
            "phone": "254712345678",
            "password": "Customer-password-123",
        },
    )
    assert registration.status_code == 201

    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        user, changed = seed_admin.seed_admin(
            db,
            email="existing-customer@example.com",
            promote_existing=True,
        )
        assert changed is True
        assert user.role is Role.ADMIN

        with pytest.raises(ValueError, match="already exists"):
            seed_admin.seed_admin(db, email="existing-customer@example.com")
    finally:
        generator.close()


def test_seed_admin_cli_promotes_existing_without_printing_password(client, monkeypatch, capsys):
    registration = client.post(
        "/api/auth/register",
        json={
            "full_name": "Existing Customer",
            "email": "promote-admin@example.com",
            "phone": "254712345678",
            "password": "Customer-password-123",
        },
    )
    assert registration.status_code == 201

    generator = client.app.dependency_overrides[get_db]()
    test_db = next(generator)
    try:
        @contextmanager
        def fake_session():
            yield test_db

        monkeypatch.setattr(seed_admin, "SessionLocal", fake_session)
        seed_admin.main(["promote-admin@example.com", "--promote-existing"])
        assert capsys.readouterr().out == "Admin access granted to promote-admin@example.com.\n"
        assert test_db.query(User).filter_by(email="promote-admin@example.com").one().role is Role.ADMIN
    finally:
        generator.close()
