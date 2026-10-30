from contextlib import contextmanager
from datetime import date, timedelta

from app.core.database import get_db
from app.jobs import check_expiry
from app.models import AuditLog, Role, User, Vehicle, VehicleApprovalStatus
from app.services.expiry import check_vehicle_expiry, list_expiring_vehicles


def register_admin(client):
    registration = client.post(
        "/api/auth/register",
        json={
            "full_name": "Expiry Admin",
            "email": "expiry-admin@example.com",
            "phone": "254712345678",
            "password": "CorrectHorseBattery9",
        },
    )
    assert registration.status_code == 201
    headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}
    admin_id = registration.json()["user"]["id"]

    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        admin = db.get(User, admin_id)
        assert admin is not None
        admin.role = Role.ADMIN
        db.commit()
    finally:
        generator.close()
    return headers, admin_id


def seed_vehicle(db, plate: str, *, status: VehicleApprovalStatus, insurance, inspection) -> Vehicle:
    vehicle = Vehicle(
        make="Toyota",
        model="Corolla",
        year=2022,
        plate=plate,
        chassis_number=f"CHASSIS-{plate}",
        seats=5,
        transmission="automatic",
        fuel_type="petrol",
        daily_rate=4500,
        deposit_amount=10000,
        insurance_expiry=insurance,
        inspection_expiry=inspection,
        approval_status=status,
        location="Nairobi",
    )
    db.add(vehicle)
    db.flush()
    return vehicle


def test_expiry_check_suspends_expired_approved_vehicles_and_audits(client):
    headers, admin_id = register_admin(client)
    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    today = date.today()
    try:
        expired_insurance = seed_vehicle(
            db,
            "KDE111A",
            status=VehicleApprovalStatus.APPROVED,
            insurance=today - timedelta(days=1),
            inspection=today + timedelta(days=30),
        )
        expired_inspection = seed_vehicle(
            db,
            "KDE222A",
            status=VehicleApprovalStatus.APPROVED,
            insurance=today + timedelta(days=30),
            inspection=today - timedelta(days=1),
        )
        pending_expired = seed_vehicle(
            db,
            "KDE333A",
            status=VehicleApprovalStatus.PENDING,
            insurance=today - timedelta(days=1),
            inspection=today - timedelta(days=1),
        )
        db.commit()

        response = client.post("/api/admin/jobs/check-expiry", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["suspended_count"] == 2
        assert set(body["vehicle_ids"]) == {expired_insurance.id, expired_inspection.id}

        db.expire_all()
        for vehicle_id in body["vehicle_ids"]:
            vehicle = db.get(Vehicle, vehicle_id)
            assert vehicle is not None
            assert vehicle.approval_status is VehicleApprovalStatus.SUSPENDED
            assert vehicle.rejection_reason == "Document expired"
            audit = db.query(AuditLog).filter_by(target_id=vehicle_id, target_type="vehicle").one()
            assert audit.actor_id == admin_id
            assert audit.action == "suspend"
            assert audit.reason == "Document expired"

        assert db.get(Vehicle, pending_expired.id).approval_status is VehicleApprovalStatus.PENDING

        repeated = client.post("/api/admin/jobs/check-expiry", headers=headers)
        assert repeated.json()["suspended_count"] == 0
        db.expire_all()
        assert db.query(AuditLog).filter_by(target_type="vehicle").count() == 2
    finally:
        generator.close()


def test_expiring_list_returns_approved_vehicles_within_fourteen_days(client):
    headers, _ = register_admin(client)
    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    today = date.today()
    try:
        insurance_soon = seed_vehicle(
            db,
            "KDF111A",
            status=VehicleApprovalStatus.APPROVED,
            insurance=today + timedelta(days=14),
            inspection=today + timedelta(days=60),
        )
        inspection_soon = seed_vehicle(
            db,
            "KDF222A",
            status=VehicleApprovalStatus.APPROVED,
            insurance=today + timedelta(days=60),
            inspection=today + timedelta(days=3),
        )
        seed_vehicle(
            db,
            "KDF333A",
            status=VehicleApprovalStatus.APPROVED,
            insurance=today + timedelta(days=15),
            inspection=today + timedelta(days=60),
        )
        seed_vehicle(
            db,
            "KDF444A",
            status=VehicleApprovalStatus.PENDING,
            insurance=today + timedelta(days=2),
            inspection=today + timedelta(days=2),
        )
        db.commit()

        expiring = list_expiring_vehicles(db)
        assert {vehicle.plate for vehicle in expiring} == {"KDF111A", "KDF222A"}

        response = client.get("/api/admin/vehicles/expiring", headers=headers)
        assert response.status_code == 200
        assert {vehicle["id"] for vehicle in response.json()} == {
            insurance_soon.id,
            inspection_soon.id,
        }
        dashboard = client.get("/api/admin/dashboard", headers=headers)
        assert dashboard.status_code == 200
        assert dashboard.json()["expiring_documents"] == 2
    finally:
        generator.close()


def test_expiry_job_cli_runs_service_and_prints_summary(client, monkeypatch, capsys):
    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    today = date.today()
    try:
        seed_vehicle(
            db,
            "KDG111A",
            status=VehicleApprovalStatus.APPROVED,
            insurance=today - timedelta(days=1),
            inspection=today + timedelta(days=30),
        )
        db.commit()

        @contextmanager
        def fake_session():
            yield db

        monkeypatch.setattr(check_expiry, "SessionLocal", fake_session)
        check_expiry.main()
        assert capsys.readouterr().out == "Suspended 1 expired vehicle(s).\n"
        db.expire_all()
        audit = db.query(AuditLog).filter_by(target_type="vehicle").one()
        assert audit.actor_id is None
        assert audit.reason == "Document expired"
    finally:
        generator.close()


def test_expiry_admin_endpoints_require_admin(client):
    registration = client.post(
        "/api/auth/register",
        json={
            "full_name": "Regular User",
            "email": "regular-expiry@example.com",
            "phone": "254712345678",
            "password": "CorrectHorseBattery9",
        },
    )
    headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}

    assert client.post("/api/admin/jobs/check-expiry", headers=headers).status_code == 403
    assert client.get("/api/admin/vehicles/expiring", headers=headers).status_code == 403
    assert client.get("/api/admin/dashboard", headers=headers).status_code == 403
    assert client.get("/api/admin/audit", headers=headers).status_code == 403
