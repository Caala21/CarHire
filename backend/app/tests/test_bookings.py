from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.core.database import get_db
from app.models import (
    Booking,
    BookingStatus,
    OwnerProfile,
    OwnerVerificationStatus,
    Role,
    User,
    Vehicle,
    VehicleApprovalStatus,
)


def register_customer(client, email: str, *, verified: bool = True):
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Booking Customer",
            "email": email,
            "phone": "254712345678",
            "password": "CorrectHorseBattery9",
        },
    )
    assert response.status_code == 201
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    if verified:
        generator = client.app.dependency_overrides[get_db]()
        db = next(generator)
        try:
            user = db.get(User, response.json()["user"]["id"])
            assert user is not None
            user.phone_verified_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            generator.close()
    return headers, response.json()["user"]["id"]


def create_public_vehicle(client, *, owner_id: int | None = None) -> int:
    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        vehicle = Vehicle(
            owner_id=owner_id,
            make="Toyota",
            model="Corolla",
            year=2024,
            plate=f"KDA{db.query(Vehicle).count() + 100}A",
            chassis_number=f"BOOKING-CHASSIS-{db.query(Vehicle).count() + 100}",
            logbook_url="/api/files/1",
            insurance_url="/api/files/2",
            insurance_expiry=date.today() + timedelta(days=180),
            inspection_expiry=date.today() + timedelta(days=180),
            approval_status=VehicleApprovalStatus.APPROVED,
            seats=5,
            transmission="automatic",
            fuel_type="petrol",
            daily_rate=Decimal("100.50"),
            deposit_amount=Decimal("50.00"),
            location="Nairobi",
        )
        db.add(vehicle)
        db.commit()
        return vehicle.id
    finally:
        generator.close()


def booking_payload(vehicle_id: int, start_offset: int = 3, end_offset: int = 5):
    return {
        "vehicle_id": vehicle_id,
        "start_date": (date.today() + timedelta(days=start_offset)).isoformat(),
        "end_date": (date.today() + timedelta(days=end_offset)).isoformat(),
    }


def test_booking_requires_verified_phone_and_valid_future_date_range(client):
    headers, _ = register_customer(client, "booking-unverified@example.com", verified=False)
    vehicle_id = create_public_vehicle(client)

    response = client.post(
        "/api/bookings",
        json=booking_payload(vehicle_id),
        headers=headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "phone_not_verified"

    verified_headers, _ = register_customer(client, "booking-verified@example.com")
    past = client.post(
        "/api/bookings",
        json={
            "vehicle_id": vehicle_id,
            "start_date": (date.today() - timedelta(days=1)).isoformat(),
            "end_date": date.today().isoformat(),
        },
        headers=verified_headers,
    )
    assert past.status_code == 422
    assert "start_date cannot be in the past" in past.json()["error"]["details"][0]["message"]

    reversed_dates = client.post(
        "/api/bookings",
        json={
            "vehicle_id": vehicle_id,
            "start_date": (date.today() + timedelta(days=2)).isoformat(),
            "end_date": (date.today() + timedelta(days=2)).isoformat(),
        },
        headers=verified_headers,
    )
    assert reversed_dates.status_code == 422
    assert "end_date must be after start_date" in reversed_dates.json()["error"]["details"][0]["message"]


def test_create_booking_prices_total_sets_expiration_and_blocks_overlaps(client):
    headers, customer_id = register_customer(client, "booking-create@example.com")
    vehicle_id = create_public_vehicle(client)

    created = client.post(
        "/api/bookings",
        json=booking_payload(vehicle_id),
        headers=headers,
    )
    assert created.status_code == 201
    body = created.json()
    assert body["customer_id"] == customer_id
    assert body["status"] == "pending"
    assert Decimal(body["total_price"]) == Decimal("251.00")
    assert Decimal(body["deposit_amount"]) == Decimal("50.00")
    assert body["deposit_paid"] is False
    expires_at = datetime.fromisoformat(body["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    assert expires_at > datetime.now(timezone.utc)

    overlap = client.post(
        "/api/bookings",
        json=booking_payload(vehicle_id, start_offset=4, end_offset=6),
        headers=headers,
    )
    assert overlap.status_code == 409
    assert overlap.json()["error"]["code"] == "vehicle_unavailable"

    adjacent = client.post(
        "/api/bookings",
        json=booking_payload(vehicle_id, start_offset=5, end_offset=6),
        headers=headers,
    )
    assert adjacent.status_code == 201

    availability = client.get(
        f"/api/vehicles/{vehicle_id}/availability",
        params={
            "from": (date.today() + timedelta(days=2)).isoformat(),
            "to": (date.today() + timedelta(days=8)).isoformat(),
        },
    )
    assert availability.status_code == 200
    assert availability.json()["blocked_ranges"] == [
        {
            "start_date": (date.today() + timedelta(days=3)).isoformat(),
            "end_date": (date.today() + timedelta(days=5)).isoformat(),
        },
        {
            "start_date": (date.today() + timedelta(days=5)).isoformat(),
            "end_date": (date.today() + timedelta(days=6)).isoformat(),
        },
    ]


def test_non_public_vehicle_cannot_be_booked_or_checked_for_availability(client):
    headers, _ = register_customer(client, "booking-private@example.com")
    vehicle_id = create_public_vehicle(client)
    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        vehicle = db.get(Vehicle, vehicle_id)
        assert vehicle is not None
        vehicle.approval_status = VehicleApprovalStatus.PENDING
        db.commit()
    finally:
        generator.close()

    response = client.post(
        "/api/bookings",
        json=booking_payload(vehicle_id),
        headers=headers,
    )
    assert response.status_code == 404
    assert client.get(
        f"/api/vehicles/{vehicle_id}/availability",
        params={
            "from": date.today().isoformat(),
            "to": (date.today() + timedelta(days=10)).isoformat(),
        },
    ).status_code == 404


@pytest.mark.parametrize(
    "reason",
    ["owner_pending", "insurance_expired", "inspection_expired", "insurance_missing"],
)
def test_booking_requires_approved_owner_and_current_documents(client, reason):
    headers, _ = register_customer(client, f"booking-{reason}@example.com")
    _, owner_id = register_customer(client, f"booking-{reason}-owner@example.com")
    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        db.add(
            OwnerProfile(
                user_id=owner_id,
                national_id=f"NAT-{reason}",
                kra_pin=f"A{len(reason)}123456Z",
                payout_phone="254712345678",
                verification_status=(
                    OwnerVerificationStatus.PENDING
                    if reason == "owner_pending"
                    else OwnerVerificationStatus.APPROVED
                ),
            )
        )
        db.commit()
    finally:
        generator.close()

    vehicle_id = create_public_vehicle(client, owner_id=owner_id)
    if reason != "owner_pending":
        generator = client.app.dependency_overrides[get_db]()
        db = next(generator)
        try:
            vehicle = db.get(Vehicle, vehicle_id)
            assert vehicle is not None
            if reason == "insurance_expired":
                vehicle.insurance_expiry = date.today() - timedelta(days=1)
            elif reason == "inspection_expired":
                vehicle.inspection_expiry = date.today() - timedelta(days=1)
            else:
                vehicle.insurance_url = None
            db.commit()
        finally:
            generator.close()

    response = client.post(
        "/api/bookings",
        json=booking_payload(vehicle_id),
        headers=headers,
    )
    assert response.status_code == 404


def test_customer_can_cancel_future_booking_but_not_started_booking(client):
    headers, _ = register_customer(client, "booking-cancel@example.com")
    other_headers, _ = register_customer(client, "booking-cancel-other@example.com")
    vehicle_id = create_public_vehicle(client)
    created = client.post("/api/bookings", json=booking_payload(vehicle_id), headers=headers)
    assert created.status_code == 201

    unauthorized = client.post(
        f"/api/bookings/{created.json()['id']}/cancel",
        headers=other_headers,
    )
    assert unauthorized.status_code == 404

    cancelled = client.post(f"/api/bookings/{created.json()['id']}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    started = client.post(
        "/api/bookings",
        json=booking_payload(vehicle_id, start_offset=0, end_offset=1),
        headers=headers,
    )
    assert started.status_code == 201
    cannot_cancel = client.post(
        f"/api/bookings/{started.json()['id']}/cancel",
        headers=headers,
    )
    assert cannot_cancel.status_code == 409


def test_booking_lists_are_scoped_for_customers_owners_and_admins(client):
    headers, customer_id = register_customer(client, "booking-owner-customer@example.com")
    owner_headers, owner_id = register_customer(client, "booking-owner@example.com")
    admin_headers, _ = register_customer(client, "booking-admin@example.com")
    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        owner = db.get(User, owner_id)
        admin = db.get(User, int(client.get("/api/auth/me", headers=admin_headers).json()["id"]))
        assert owner is not None and admin is not None
        owner.role = Role.OWNER
        admin.role = Role.ADMIN
        db.add(
            OwnerProfile(
                user_id=owner_id,
                national_id="NAT-BOOKING-OWNER",
                kra_pin="A12345678Z",
                payout_phone="254712345678",
                verification_status=OwnerVerificationStatus.APPROVED,
            )
        )
        db.commit()
    finally:
        generator.close()

    vehicle_id = create_public_vehicle(client, owner_id=owner_id)
    created = client.post(
        "/api/bookings",
        json=booking_payload(vehicle_id),
        headers=headers,
    )
    assert created.status_code == 201
    assert client.get("/api/bookings/me", headers=headers).json()[0]["id"] == created.json()["id"]
    assert client.get("/api/owners/me/bookings", headers=owner_headers).json()[0]["id"] == created.json()["id"]
    assert client.get("/api/admin/bookings", headers=admin_headers).json()[0]["id"] == created.json()["id"]
    assert client.get("/api/admin/bookings", headers=headers).status_code == 403

    other_owner_headers, _ = register_customer(client, "booking-other-owner@example.com")
    assert client.get("/api/owners/me/bookings", headers=other_owner_headers).status_code == 403


def test_expired_unpaid_booking_is_released_during_availability_check(client):
    headers, _ = register_customer(client, "booking-expired@example.com")
    vehicle_id = create_public_vehicle(client)
    created = client.post("/api/bookings", json=booking_payload(vehicle_id), headers=headers)
    assert created.status_code == 201

    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        booking = db.get(Booking, created.json()["id"])
        assert booking is not None
        booking.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    finally:
        generator.close()

    availability = client.get(
        f"/api/vehicles/{vehicle_id}/availability",
        params={
            "from": (date.today() + timedelta(days=2)).isoformat(),
            "to": (date.today() + timedelta(days=8)).isoformat(),
        },
    )
    assert availability.status_code == 200
    assert availability.json()["blocked_ranges"] == []

    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        expired = db.get(Booking, created.json()["id"])
        assert expired is not None
        assert expired.status is BookingStatus.CANCELLED
    finally:
        generator.close()

    replacement = client.post(
        "/api/bookings",
        json=booking_payload(vehicle_id),
        headers=headers,
    )
    assert replacement.status_code == 201
