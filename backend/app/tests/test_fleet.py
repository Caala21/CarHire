from datetime import date, datetime, timedelta, timezone
import logging

import pytest

from app.core.database import get_db
from app.main import CoordinateQueryRedactionFilter
from app.models import (
    AuditLog,
    OwnerProfile,
    Role,
    User,
    Vehicle,
    VehicleApprovalStatus,
)
from app.services.storage import storage

PDF_BYTES = b"%PDF-1.7\nfleet document\n"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"test-image"


@pytest.fixture
def isolated_uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "base_dir", tmp_path)


def register(client, email: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Amina Wanjiku",
            "email": email,
            "phone": "254712345678",
            "password": "CorrectHorseBattery9",
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def update_user(client, user_id: int, **fields) -> None:
    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        user = db.get(User, user_id)
        assert user is not None
        for field, value in fields.items():
            setattr(user, field, value)
        db.commit()
    finally:
        generator.close()


def user_id_from_header(client, headers: dict[str, str]) -> int:
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    return response.json()["id"]


def apply_owner(client, email: str) -> tuple[dict[str, str], int]:
    headers = register(client, email)
    owner_id = user_id_from_header(client, headers)
    update_user(client, owner_id, phone_verified_at=datetime.now(timezone.utc))
    response = client.post(
        "/api/owners/apply",
        json={
            "national_id": f"NAT-{owner_id}-12345",
            "kra_pin": f"A00{owner_id}12345Z",
            "payout_phone": "254712345678",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return headers, owner_id


def upload_owner_documents(client, headers: dict[str, str]) -> None:
    for document_type in ("id", "selfie"):
        response = client.post(
            "/api/owners/me/documents",
            data={"document_type": document_type},
            files={"file": ("document.pdf", PDF_BYTES, "application/pdf")},
            headers=headers,
        )
        assert response.status_code == 201


def create_admin(client, email: str = "admin-fleet@example.com") -> dict[str, str]:
    headers = register(client, email)
    admin_id = user_id_from_header(client, headers)
    update_user(client, admin_id, role=Role.ADMIN)
    return headers


def approve_owner(client, headers: dict[str, str], owner_id: int) -> None:
    upload_owner_documents(client, headers)
    admin_headers = create_admin(client, f"admin-fleet-{owner_id}@example.com")
    response = client.post(f"/api/admin/owners/{owner_id}/approve", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["verification_status"] == "approved"
    assert "national_id" not in response.json()
    assert "kra_pin" not in response.json()


def vehicle_payload(plate: str = "KDA123A") -> dict:
    expiry = date.today() + timedelta(days=180)
    return {
        "make": "Toyota",
        "model": "Corolla",
        "year": 2022,
        "plate": plate,
        "chassis_number": f"CHASSIS-{plate}",
        "seats": 5,
        "transmission": "automatic",
        "fuel_type": "petrol",
        "daily_rate": "4500.00",
        "deposit_amount": "10000.00",
        "insurance_expiry": expiry.isoformat(),
        "inspection_expiry": expiry.isoformat(),
        "location": "Nairobi",
    }


def test_owner_apply_requires_verified_phone_and_stays_pending(client):
    headers = register(client, "apply-owner@example.com")
    response = client.post(
        "/api/owners/apply",
        json={
            "national_id": "NAT-1234567",
            "kra_pin": "A001234567Z",
            "payout_phone": "254712345678",
        },
        headers=headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "phone_not_verified"

    owner_id = user_id_from_header(client, headers)
    update_user(client, owner_id, phone_verified_at=datetime.now(timezone.utc))
    applied = client.post(
        "/api/owners/apply",
        json={
            "national_id": "NAT-1234567",
            "kra_pin": "A001234567Z",
            "payout_phone": "254712345678",
        },
        headers=headers,
    )

    assert applied.status_code == 201
    assert applied.json()["verification_status"] == "pending"
    assert client.get("/api/auth/me", headers=headers).json()["role"] == "customer"


def test_admin_approves_owner_and_audits_action(client, isolated_uploads):
    headers, owner_id = apply_owner(client, "owner-approval@example.com")
    upload_owner_documents(client, headers)
    admin_headers = create_admin(client)

    detail = client.get(f"/api/admin/owners/{owner_id}", headers=admin_headers)
    assert detail.status_code == 200
    assert detail.json()["national_id"] == f"NAT-{owner_id}-12345"
    assert detail.json()["kra_pin"] == f"A00{owner_id}12345Z"
    assert detail.json()["payout_phone"] == "254712345678"

    pending = client.get("/api/admin/owners?status=pending", headers=admin_headers)
    assert pending.status_code == 200
    assert [profile["user_id"] for profile in pending.json()] == [owner_id]
    assert "national_id" not in pending.text
    assert "kra_pin" not in pending.text
    for document_field in ("id_document_download_url", "selfie_document_download_url"):
        assert pending.json()[0][document_field]
        document = client.get(
            pending.json()[0][document_field],
            headers=admin_headers,
        )
        assert document.status_code == 200

    approved = client.post(
        f"/api/admin/owners/{owner_id}/approve",
        headers=admin_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["verification_status"] == "approved"
    assert client.get("/api/auth/me", headers=headers).json()["role"] == "owner"
    audit_trail = client.get("/api/admin/audit", headers=admin_headers)
    assert audit_trail.status_code == 200
    assert audit_trail.json()[0]["action"] == "approve"
    dashboard = client.get("/api/admin/dashboard", headers=admin_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["pending_owners"] == 0

    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        audit = db.query(AuditLog).filter_by(target_type="owner", target_id=owner_id).one()
        assert audit.action == "approve"
        assert audit.actor_id == user_id_from_header(client, admin_headers)
        profile = db.get(OwnerProfile, owner_id)
        assert profile is not None
        assert profile.national_id == f"NAT-{owner_id}-12345"
    finally:
        generator.close()


def test_approved_owner_creates_pending_vehicle_hidden_from_public(client, isolated_uploads):
    owner_headers, _ = apply_owner(client, "vehicle-owner@example.com")
    approve_owner(client, owner_headers, user_id_from_header(client, owner_headers))

    created = client.post(
        "/api/vehicles",
        json=vehicle_payload(),
        headers=owner_headers,
    )
    assert created.status_code == 201
    assert created.json()["approval_status"] == "pending"
    vehicle_id = created.json()["id"]

    listing = client.get("/api/vehicles")
    assert listing.status_code == 200
    assert listing.json()["items"] == []
    assert client.get(f"/api/vehicles/{vehicle_id}").status_code == 404


def test_pending_owner_can_submit_vehicle_for_review(client, isolated_uploads):
    owner_headers, _ = apply_owner(client, "pending-vehicle-owner@example.com")

    application = client.get("/api/owners/me", headers=owner_headers)
    assert application.status_code == 200
    assert application.json()["verification_status"] == "pending"

    created = client.post(
        "/api/vehicles",
        json=vehicle_payload(),
        headers=owner_headers,
    )
    assert created.status_code == 201
    assert created.json()["approval_status"] == "pending"
    vehicle_id = created.json()["id"]

    for document_type in ("logbook", "insurance"):
        uploaded = client.post(
            f"/api/vehicles/{vehicle_id}/documents",
            data={"document_type": document_type},
            files={"file": ("document.pdf", PDF_BYTES, "application/pdf")},
            headers=owner_headers,
        )
        assert uploaded.status_code == 201

    photo = client.post(
        f"/api/vehicles/{vehicle_id}/photos",
        files={"file": ("photo.png", PNG_BYTES, "image/png")},
        headers=owner_headers,
    )
    assert photo.status_code == 201
    assert client.get("/api/owners/me/vehicles", headers=owner_headers).json()[0][
        "approval_status"
    ] == "pending"


def test_admin_can_review_pending_vehicle_photo_and_dashboard(client, isolated_uploads):
    owner_headers, _ = apply_owner(client, "admin-photo-owner@example.com")
    admin_headers = create_admin(client, "admin-photo-reviewer@example.com")
    created = client.post(
        "/api/vehicles",
        json=vehicle_payload("KDC456B"),
        headers=owner_headers,
    )
    vehicle_id = created.json()["id"]
    uploaded = client.post(
        f"/api/vehicles/{vehicle_id}/photos",
        files={"file": ("photo.png", PNG_BYTES, "image/png")},
        headers=owner_headers,
    )
    assert uploaded.status_code == 201

    pending = client.get("/api/admin/vehicles", headers=admin_headers)
    assert pending.status_code == 200
    admin_vehicle = next(item for item in pending.json() if item["id"] == vehicle_id)
    assert admin_vehicle["owner_name"] == "Amina Wanjiku"
    file_id = int(admin_vehicle["photos"][0].rsplit("/", 1)[1])
    photo = client.get(f"/api/admin/vehicle-photos/{file_id}", headers=admin_headers)
    assert photo.status_code == 200
    assert photo.content == PNG_BYTES
    assert client.get(
        f"/api/admin/vehicle-photos/{file_id}",
        headers=owner_headers,
    ).status_code == 403

    dashboard = client.get("/api/admin/dashboard", headers=admin_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["pending_owners"] == 1
    assert dashboard.json()["pending_vehicles"] == 1
    assert dashboard.json()["expiring_documents"] == 0


def test_owner_cannot_edit_another_owners_vehicle(client, isolated_uploads):
    first_headers, _ = apply_owner(client, "first-vehicle-owner@example.com")
    approve_owner(client, first_headers, user_id_from_header(client, first_headers))
    second_headers, _ = apply_owner(client, "second-vehicle-owner@example.com")
    approve_owner(client, second_headers, user_id_from_header(client, second_headers))

    created = client.post(
        "/api/vehicles",
        json=vehicle_payload(),
        headers=first_headers,
    )
    assert created.status_code == 201

    attempted = client.patch(
        f"/api/vehicles/{created.json()['id']}",
        json={"plate": "KDB999Z"},
        headers=second_headers,
    )
    assert attempted.status_code == 403
    assert attempted.json()["error"]["code"] == "forbidden"


def test_vehicle_upload_rejects_bad_type_content_and_oversize(client, isolated_uploads):
    owner_headers, owner_id = apply_owner(client, "upload-owner@example.com")
    approve_owner(client, owner_headers, owner_id)
    created = client.post(
        "/api/vehicles",
        json=vehicle_payload(),
        headers=owner_headers,
    )
    vehicle_id = created.json()["id"]

    invalid_type = client.post(
        f"/api/vehicles/{vehicle_id}/documents",
        data={"document_type": "logbook"},
        files={"file": ("script.txt", b"not a document", "text/plain")},
        headers=owner_headers,
    )
    assert invalid_type.status_code == 422

    invalid_content = client.post(
        f"/api/vehicles/{vehicle_id}/documents",
        data={"document_type": "logbook"},
        files={"file": ("fake.pdf", b"not a pdf", "application/pdf")},
        headers=owner_headers,
    )
    assert invalid_content.status_code == 422

    oversized = client.post(
        f"/api/vehicles/{vehicle_id}/documents",
        data={"document_type": "logbook"},
        files={"file": ("large.pdf", b"%PDF-" + b"x" * (5 * 1024 * 1024), "application/pdf")},
        headers=owner_headers,
    )
    assert oversized.status_code == 413


def test_approved_vehicle_document_download_and_public_response_privacy(client, isolated_uploads):
    owner_headers, owner_id = apply_owner(client, "public-owner@example.com")
    approve_owner(client, owner_headers, owner_id)
    admin_headers = create_admin(client)
    created = client.post(
        "/api/vehicles",
        json=vehicle_payload("KDA333A"),
        headers=owner_headers,
    )
    vehicle_id = created.json()["id"]
    uploaded_ids = []
    for document_type in ("logbook", "insurance"):
        response = client.post(
            f"/api/vehicles/{vehicle_id}/documents",
            data={"document_type": document_type},
            files={"file": (f"{document_type}.pdf", PDF_BYTES, "application/pdf")},
            headers=owner_headers,
        )
        assert response.status_code == 201
        uploaded_ids.append(response.json()["file_id"])

    pending = client.get("/api/admin/vehicles?status=pending", headers=admin_headers)
    admin_vehicle = next(item for item in pending.json() if item["id"] == vehicle_id)
    assert admin_vehicle["logbook_download_url"] == f"/api/files/{uploaded_ids[0]}"
    assert admin_vehicle["insurance_download_url"] == f"/api/files/{uploaded_ids[1]}"
    assert client.get(
        admin_vehicle["logbook_download_url"],
        headers=admin_headers,
    ).status_code == 200

    approved = client.post(
        f"/api/admin/vehicles/{vehicle_id}/approve",
        headers=admin_headers,
    )
    assert approved.status_code == 200
    assert "logbook_url" not in approved.json()
    assert "insurance_url" not in approved.json()

    listing = client.get("/api/vehicles").json()
    assert listing["total"] == 1
    assert "logbook_url" not in listing["items"][0]
    assert "insurance_url" not in listing["items"][0]
    assert "national_id" not in listing["items"][0]
    assert "kra_pin" not in listing["items"][0]

    owner_download = client.get(f"/api/files/{uploaded_ids[0]}", headers=owner_headers)
    assert owner_download.status_code == 200
    other_user = register(client, "document-outsider@example.com")
    assert client.get(
        f"/api/files/{uploaded_ids[0]}",
        headers=other_user,
    ).status_code == 403
    assert client.get(
        f"/api/files/{uploaded_ids[0]}",
        headers=admin_headers,
    ).status_code == 200


def test_public_vehicle_photo_upload_is_capped_at_eight(client, isolated_uploads):
    owner_headers, owner_id = apply_owner(client, "photo-owner@example.com")
    approve_owner(client, owner_headers, owner_id)
    outsider_headers = register(client, "photo-outsider@example.com")
    created = client.post(
        "/api/vehicles",
        json=vehicle_payload("KDA444A"),
        headers=owner_headers,
    )
    vehicle_id = created.json()["id"]

    for document_type in ("logbook", "insurance"):
        uploaded_document = client.post(
            f"/api/vehicles/{vehicle_id}/documents",
            data={"document_type": document_type},
            files={"file": (f"{document_type}.pdf", PDF_BYTES, "application/pdf")},
            headers=owner_headers,
        )
        assert uploaded_document.status_code == 201
    admin_headers = create_admin(client, "photo-admin@example.com")
    approved = client.post(
        f"/api/admin/vehicles/{vehicle_id}/approve",
        headers=admin_headers,
    )
    assert approved.status_code == 200

    openapi = client.get("/openapi.json").json()
    assert "post" in openapi["paths"]["/api/vehicles/{vehicle_id}/photos"]
    assert "get" in openapi["paths"]["/api/public/vehicle-photos/{file_id}"]

    forbidden = client.post(
        f"/api/vehicles/{vehicle_id}/photos",
        files={"file": ("car.png", PNG_BYTES, "image/png")},
        headers=outsider_headers,
    )
    assert forbidden.status_code == 403

    invalid_type = client.post(
        f"/api/vehicles/{vehicle_id}/photos",
        files={"file": ("car.gif", b"GIF89a", "image/gif")},
        headers=owner_headers,
    )
    assert invalid_type.status_code == 422
    oversized = client.post(
        f"/api/vehicles/{vehicle_id}/photos",
        files={
            "file": (
                "large.png",
                b"\x89PNG\r\n\x1a\n" + b"x" * (5 * 1024 * 1024),
                "image/png",
            )
        },
        headers=owner_headers,
    )
    assert oversized.status_code == 413

    photo_urls = []
    for _ in range(8):
        uploaded = client.post(
            f"/api/vehicles/{vehicle_id}/photos",
            files={"file": ("car.png", PNG_BYTES, "image/png")},
            headers=owner_headers,
        )
        assert uploaded.status_code == 201
        photo_urls.append(uploaded.json()["download_url"])

    ninth = client.post(
        f"/api/vehicles/{vehicle_id}/photos",
        files={"file": ("car.png", PNG_BYTES, "image/png")},
        headers=owner_headers,
    )
    assert ninth.status_code == 409
    assert len(photo_urls) == 8
    public_photo = client.get(photo_urls[0])
    assert public_photo.status_code == 200
    assert public_photo.content == PNG_BYTES

    listing = client.get("/api/vehicles").json()
    listed_vehicle = next(item for item in listing["items"] if item["id"] == vehicle_id)
    detail = client.get(f"/api/vehicles/{vehicle_id}").json()
    assert listed_vehicle["photos"] == photo_urls
    assert detail["photos"] == photo_urls


def test_vehicle_coordinates_are_private_and_owner_can_edit_them(client, isolated_uploads):
    owner_headers, owner_id = apply_owner(client, "location-owner@example.com")
    approve_owner(client, owner_headers, owner_id)
    admin_headers = create_admin(client, "location-admin@example.com")
    payload = vehicle_payload("KDL678A")
    payload.update(
        area_name="Westlands, Nairobi",
        latitude=-1.2676,
        longitude=36.8108,
    )
    created = client.post("/api/vehicles", json=payload, headers=owner_headers)
    assert created.status_code == 201
    vehicle_id = created.json()["id"]

    owned = client.get("/api/owners/me/vehicles", headers=owner_headers).json()[0]
    assert owned["latitude"] == -1.2676
    assert owned["longitude"] == 36.8108
    pending = client.get("/api/admin/vehicles", headers=admin_headers).json()
    admin_vehicle = next(item for item in pending if item["id"] == vehicle_id)
    assert admin_vehicle["latitude"] == -1.2676
    assert admin_vehicle["longitude"] == 36.8108

    updated = client.patch(
        f"/api/vehicles/{vehicle_id}",
        json={
            "area_name": "Kilimani, Nairobi",
            "location": "Kilimani, Nairobi",
            "latitude": -1.2921,
            "longitude": 36.7875,
        },
        headers=owner_headers,
    )
    assert updated.status_code == 200
    owned = client.get("/api/owners/me/vehicles", headers=owner_headers).json()[0]
    assert owned["area_name"] == "Kilimani, Nairobi"
    assert owned["latitude"] == -1.2921
    assert owned["longitude"] == 36.7875

    for document_type in ("logbook", "insurance"):
        uploaded = client.post(
            f"/api/vehicles/{vehicle_id}/documents",
            data={"document_type": document_type},
            files={"file": (f"{document_type}.pdf", PDF_BYTES, "application/pdf")},
            headers=owner_headers,
        )
        assert uploaded.status_code == 201
    approved = client.post(
        f"/api/admin/vehicles/{vehicle_id}/approve",
        headers=admin_headers,
    )
    assert approved.status_code == 200
    for item in client.get("/api/vehicles").json()["items"]:
        assert "latitude" not in item and "longitude" not in item
        if item["id"] == vehicle_id:
            assert item["area_name"] == "Kilimani, Nairobi"
    public_detail = client.get(f"/api/vehicles/{vehicle_id}")
    assert public_detail.status_code == 200
    assert public_detail.json()["area_name"] == "Kilimani, Nairobi"
    assert "latitude" not in public_detail.json()
    assert "longitude" not in public_detail.json()


def test_nearby_vehicle_search_sorts_by_distance_and_limits_radius(client):
    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        coordinates = [
            ("KDA100A", "Closest", -1.2864, 36.8172),
            ("KDA101A", "Nearby", -1.3000, 36.8200),
            ("KDA102A", "Far", -4.0435, 39.6682),
        ]
        for plate, area_name, latitude, longitude in coordinates:
            db.add(
                Vehicle(
                    make="Toyota",
                    model=area_name,
                    year=2024,
                    plate=plate,
                    chassis_number=f"LOCATION-{plate}",
                    insurance_url="/api/files/insurance",
                    insurance_expiry=date.today() + timedelta(days=180),
                    inspection_expiry=date.today() + timedelta(days=180),
                    approval_status=VehicleApprovalStatus.APPROVED,
                    location="Kenya",
                    area_name=area_name,
                    latitude=latitude,
                    longitude=longitude,
                    seats=5,
                    transmission="automatic",
                    fuel_type="petrol",
                    daily_rate=4500,
                    deposit_amount=10000,
                )
            )
        db.commit()
    finally:
        generator.close()

    response = client.get(
        "/api/vehicles",
        params={"near_lat": -1.2864, "near_lng": 36.8172, "radius_km": 10},
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["model"] for item in items] == ["Closest", "Nearby"]
    assert [item["distance_km"] for item in items] == [0, 2]
    assert all("latitude" not in item and "longitude" not in item for item in items)
    assert all("area_name" in item for item in items)

    area_search = client.get("/api/vehicles", params={"location": "Nearby"})
    assert area_search.status_code == 200
    assert [item["area_name"] for item in area_search.json()["items"]] == ["Nearby"]

    radius_limited = client.get(
        "/api/vehicles",
        params={"near_lat": -1.2864, "near_lng": 36.8172, "radius_km": 1},
    )
    assert [item["model"] for item in radius_limited.json()["items"]] == ["Closest"]
    assert client.get("/api/vehicles", params={"near_lat": 0}).status_code == 422


def test_reverse_geocoding_is_owner_only_cached_and_uses_a_user_agent(client, monkeypatch):
    from app.services import geocoding

    owner_headers, owner_id = apply_owner(client, "geocode-owner@example.com")
    approve_owner(client, owner_headers, owner_id)
    customer_headers = register(client, "geocode-customer@example.com")
    requests = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b'{"address":{"suburb":"Westlands","city":"Nairobi"}}'

    def fake_urlopen(request, timeout):
        requests.append(request)
        assert timeout == 10
        assert request.get_header("User-agent") == (
            "CarHire/0.1 (https://github.com/Caala21/CarHire)"
        )
        return FakeResponse()

    monkeypatch.setattr(geocoding, "urlopen", fake_urlopen)
    clock = [10.0]
    waits = []

    def fake_sleep(seconds):
        waits.append(seconds)
        clock[0] += seconds

    monkeypatch.setattr(geocoding.time, "sleep", fake_sleep)
    monkeypatch.setattr(geocoding.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(geocoding, "_last_request_at", 9.5)

    payload = {"latitude": -1.26761, "longitude": 36.81081}
    first = client.post(
        "/api/vehicles/reverse-geocode",
        json=payload,
        headers=owner_headers,
    )
    second = client.post(
        "/api/vehicles/reverse-geocode",
        json={"latitude": -1.26762, "longitude": 36.81082},
        headers=owner_headers,
    )
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json() == {"area_name": "Westlands, Nairobi"}
    assert len(requests) == 1
    throttled = client.post(
        "/api/vehicles/reverse-geocode",
        json={"latitude": -1.2800, "longitude": 36.8200},
        headers=owner_headers,
    )
    assert throttled.status_code == 200
    assert len(requests) == 2
    assert waits == [0.5, 1.0]
    assert client.post(
        "/api/vehicles/reverse-geocode",
        json=payload,
        headers=customer_headers,
    ).status_code == 403


def test_nearby_coordinates_are_redacted_from_access_log_records():
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %s',
        ("127.0.0.1", "GET", "/api/vehicles?near_lat=-1.2&near_lng=36.8", "1.1", 200),
        None,
    )
    assert CoordinateQueryRedactionFilter().filter(record)
    assert "-1.2" not in record.getMessage()
    assert "36.8" not in record.getMessage()
    assert "[redacted]" in record.getMessage()
