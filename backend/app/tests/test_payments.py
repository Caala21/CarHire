import base64
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import SecretStr

from app.core.config import Settings, settings
from app.core.database import get_db
from app.models import Booking, Payment, PaymentStatus, Role, User, Vehicle, VehicleApprovalStatus
from app.services import mpesa


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(response=self)
        return None

    def json(self):
        return self.payload


@pytest.fixture
def daraja(monkeypatch):
    monkeypatch.setattr(settings, "mpesa_env", "sandbox")
    monkeypatch.setattr(settings, "mpesa_consumer_key", SecretStr("consumer-key"))
    monkeypatch.setattr(settings, "mpesa_consumer_secret", SecretStr("consumer-secret"))
    monkeypatch.setattr(settings, "mpesa_shortcode", SecretStr("174379"))
    monkeypatch.setattr(settings, "mpesa_passkey", SecretStr("pass-key"))
    monkeypatch.setattr(settings, "mpesa_callback_base_url", SecretStr("https://carhire.example"))
    monkeypatch.setattr(settings, "mpesa_callback_secret", SecretStr("callback-secret"))
    mpesa._cached_token = None
    mpesa._token_expires_at = 0
    calls = {"get": [], "post": [], "query_result": None}

    def fake_get(url, **kwargs):
        calls["get"].append((url, kwargs))
        return FakeResponse({"access_token": "temporary-token", "expires_in": "3600"})

    def fake_post(url, **kwargs):
        calls["post"].append((url, kwargs))
        if url.endswith("/mpesa/stkpush/v1/processrequest"):
            attempt = sum(
                item_url.endswith("/mpesa/stkpush/v1/processrequest")
                for item_url, _ in calls["post"]
            )
            return FakeResponse({
                "ResponseCode": "0",
                "CheckoutRequestID": f"ws_CO_{122 + attempt}",
                "MerchantRequestID": f"merchant_{122 + attempt}",
            })
        if url.endswith("/mpesa/stkpushquery/v1/query"):
            return FakeResponse(calls["query_result"] or {"ResponseCode": "0"})
        raise AssertionError(f"Unexpected Daraja endpoint: {url}")

    monkeypatch.setattr(mpesa.requests, "get", fake_get)
    monkeypatch.setattr(mpesa.requests, "post", fake_post)
    return calls


def create_booking(client, email="payer@example.com"):
    registration = client.post(
        "/api/auth/register",
        json={
            "full_name": "Payment Customer",
            "email": email,
            "phone": "254712345678",
            "password": "CorrectHorseBattery9",
        },
    )
    assert registration.status_code == 201
    user_id = registration.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}

    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        user = db.get(User, user_id)
        user.phone_verified_at = datetime.now(timezone.utc)
        vehicle = Vehicle(
            owner_id=None,
            make="Toyota",
            model="Corolla",
            year=2024,
            plate=f"KDA{db.query(Vehicle).count() + 100}A",
            chassis_number=f"PAYMENT-CHASSIS-{db.query(Vehicle).count() + 100}",
            logbook_url="/api/files/1",
            insurance_url="/api/files/2",
            insurance_expiry=date.today() + timedelta(days=180),
            inspection_expiry=date.today() + timedelta(days=180),
            approval_status=VehicleApprovalStatus.APPROVED,
            seats=5,
            transmission="automatic",
            fuel_type="petrol",
            daily_rate=Decimal("100"),
            deposit_amount=Decimal("50"),
            location="Nairobi",
        )
        db.add(vehicle)
        db.commit()
        vehicle_id = vehicle.id
    finally:
        generator.close()

    booking = client.post(
        "/api/bookings",
        headers=headers,
        json={
            "vehicle_id": vehicle_id,
            "start_date": (date.today() + timedelta(days=3)).isoformat(),
            "end_date": (date.today() + timedelta(days=5)).isoformat(),
        },
    )
    assert booking.status_code == 201
    return headers, user_id, booking.json()["id"]


def metadata(amount=50):
    return {
        "CallbackMetadata": {
            "Item": [
                {"Name": "Amount", "Value": amount},
                {"Name": "MpesaReceiptNumber", "Value": "QAB123XYZ"},
                {"Name": "PhoneNumber", "Value": 254798765432},
            ]
        }
    }


def callback(checkout_id="ws_CO_123", result_code=0, amount=50):
    return {
        "Body": {
            "stkCallback": {
                "CheckoutRequestID": checkout_id,
                "ResultCode": result_code,
                "ResultDesc": "The service request has been processed successfully",
                **metadata(amount),
            }
        }
    }


def start_payment(client, headers, booking_id):
    return client.post(
        f"/api/bookings/{booking_id}/pay",
        headers=headers,
        json={"phone": "254798765432"},
    )


def get_payment(client, headers, booking_id):
    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        return db.query(Payment).filter_by(booking_id=booking_id).one()
    finally:
        generator.close()


def test_stk_push_uses_deposit_phone_and_cached_token(client, daraja):
    headers, _, booking_id = create_booking(client)

    response = start_payment(client, headers, booking_id)
    assert response.status_code == 202
    payment = response.json()
    assert payment["amount"] == "50.00"
    assert payment["status"] == "pending"
    assert "temporary-token" not in response.text
    assert "pass-key" not in response.text
    assert "254798765432" not in response.text

    push = daraja["post"][0][1]["json"]
    assert push["Amount"] == 50
    assert push["PhoneNumber"] == "254798765432"
    assert re.fullmatch(r"\d{14}", push["Timestamp"])
    assert base64.b64decode(push["Password"]).decode() == (
        f"174379pass-key{push['Timestamp']}"
    )
    assert push["CallBackURL"] == (
        "https://carhire.example/api/payments/mpesa/callback/callback-secret"
    )
    assert push["Password"]
    assert daraja["get"][0][1]["auth"] == ("consumer-key", "consumer-secret")
    assert get_payment(client, headers, booking_id).merchant_request_id == "merchant_123"

    duplicate = start_payment(client, headers, booking_id)
    assert duplicate.status_code == 409
    assert len(daraja["post"]) == 1
    assert len(daraja["get"]) == 1


def test_callback_requires_secret_and_daraja_query_before_confirmation(client, daraja):
    headers, _, booking_id = create_booking(client)
    payment_response = start_payment(client, headers, booking_id)
    assert payment_response.status_code == 202
    daraja["query_result"] = {"ResultCode": 0}

    invalid_secret = client.post(
        "/api/payments/mpesa/callback/wrong",
        json=callback(),
    )
    assert invalid_secret.status_code == 404
    assert len(daraja["post"]) == 1

    acknowledged = client.post(
        "/api/payments/mpesa/callback/callback-secret",
        json=callback(),
    )
    assert acknowledged.status_code == 200
    assert acknowledged.json() == {"ResultCode": 0, "ResultDesc": "Accepted"}
    assert get_payment(client, headers, booking_id).status is PaymentStatus.COMPLETED

    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        booking = db.get(Booking, booking_id)
        assert booking.status.value == "confirmed"
        assert booking.deposit_paid is True
        assert db.query(Payment).filter_by(booking_id=booking_id).one().mpesa_receipt == "QAB123XYZ"
    finally:
        generator.close()

    query_count = sum("stkpushquery" in url for url, _ in daraja["post"])
    repeated = client.post("/api/payments/mpesa/callback/callback-secret", json=callback())
    assert repeated.status_code == 200
    assert sum("stkpushquery" in url for url, _ in daraja["post"]) == query_count


def test_callback_amount_mismatch_does_not_confirm_booking(client, daraja):
    headers, _, booking_id = create_booking(client)
    assert start_payment(client, headers, booking_id).status_code == 202
    daraja["query_result"] = {"ResultCode": 0}

    response = client.post(
        "/api/payments/mpesa/callback/callback-secret",
        json=callback(amount=49),
    )
    assert response.status_code == 200
    assert get_payment(client, headers, booking_id).status is PaymentStatus.FAILED

    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        assert db.get(Booking, booking_id).status.value == "pending"
    finally:
        generator.close()


def test_callback_failure_leaves_booking_pending_and_allows_retry(client, daraja):
    headers, _, booking_id = create_booking(client)
    assert start_payment(client, headers, booking_id).status_code == 202
    daraja["query_result"] = {"ResultCode": 1032, "ResultDesc": "Request cancelled by user"}

    response = client.post(
        "/api/payments/mpesa/callback/callback-secret",
        json=callback(result_code=1032),
    )
    assert response.status_code == 200
    failed = get_payment(client, headers, booking_id)
    assert failed.status is PaymentStatus.FAILED
    assert failed.result_description == "Request cancelled by user"

    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        assert db.get(Booking, booking_id).status.value == "pending"
    finally:
        generator.close()

    assert start_payment(client, headers, booking_id).status_code == 202


def test_payment_status_access_receipt_and_admin_payout_list(client, daraja):
    headers, customer_id, booking_id = create_booking(client)
    created = start_payment(client, headers, booking_id)
    assert created.status_code == 202
    daraja["query_result"] = {"ResultCode": 0}
    client.post("/api/payments/mpesa/callback/callback-secret", json=callback())
    payment_id = created.json()["id"]

    status = client.get(f"/api/payments/{payment_id}", headers=headers)
    assert status.status_code == 200
    receipt = client.get(f"/api/bookings/{booking_id}/receipt", headers=headers)
    assert receipt.status_code == 200
    assert receipt.json()["mpesa_receipt"] == "QAB123XYZ"

    stranger, _, _ = create_booking(client, "stranger@example.com")
    assert client.get(f"/api/payments/{payment_id}", headers=stranger).status_code == 404

    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        admin = db.get(User, customer_id)
        admin.role = Role.ADMIN
        db.commit()
    finally:
        generator.close()
    assert len(client.get("/api/admin/payments", headers=headers).json()) == 1
    payouts = client.get("/api/admin/payments/payouts", headers=headers)
    assert payouts.status_code == 200
    assert payouts.json()[0]["payout_status"] == "awaiting"


def test_reconciliation_finds_old_pending_and_confirms_verified_result(client, daraja):
    headers, _, booking_id = create_booking(client)
    created = start_payment(client, headers, booking_id)
    assert created.status_code == 202
    payment = get_payment(client, headers, booking_id)

    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        payment = db.get(Payment, payment.id)
        payment.created_at = datetime.now(timezone.utc) - timedelta(minutes=3)
        db.commit()
        candidates = mpesa.list_reconciliation_candidates(db)
        assert [item.id for item in candidates] == [payment.id]
        daraja["query_result"] = {"ResultCode": 0, **metadata()}
        assert mpesa.reconcile_payment(db, payment) is True
        assert payment.status is PaymentStatus.COMPLETED
    finally:
        generator.close()


def test_reconciliation_uses_staged_callback_only_after_query_confirms(client, daraja):
    headers, _, booking_id = create_booking(client)
    created = start_payment(client, headers, booking_id)
    assert created.status_code == 202
    daraja["query_result"] = {"ResponseCode": "0"}
    callback_response = client.post(
        "/api/payments/mpesa/callback/callback-secret",
        json=callback(),
    )
    assert callback_response.status_code == 200
    assert get_payment(client, headers, booking_id).status is PaymentStatus.PENDING

    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        payment = db.query(Payment).filter_by(booking_id=booking_id).one()
        payment.created_at = datetime.now(timezone.utc) - timedelta(minutes=3)
        db.commit()
        daraja["query_result"] = {"ResultCode": 0}
        assert mpesa.reconcile_payment(db, payment) is True
        assert payment.status is PaymentStatus.COMPLETED
    finally:
        generator.close()


def test_production_mpesa_settings_are_required():
    with pytest.raises(ValueError, match="all MPESA"):
        Settings(_env_file=None, mpesa_env="production")


def test_daraja_errors_keep_only_safe_codes(monkeypatch, caplog):
    response = FakeResponse(
        {"errorCode": "InvalidAccessToken", "errorMessage": "Sensitive provider detail"},
        status_code=401,
    )
    with pytest.raises(mpesa.MpesaGatewayError) as error:
        mpesa._json_response(response, phase="oauth")
    assert error.value.code == "mpesa_oauth_http_error"
    assert error.value.http_status == 401
    assert error.value.provider_code == "InvalidAccessToken"
    assert "Sensitive provider detail" not in caplog.text


def test_unverified_customer_cannot_start_stk_push(client, daraja):
    headers, _, booking_id = create_booking(client)
    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        user = db.query(User).filter_by(email="payer@example.com").one()
        user.phone_verified_at = None
        db.commit()
    finally:
        generator.close()
    response = start_payment(client, headers, booking_id)
    assert response.status_code == 403
    assert not daraja["post"]


def test_booking_stores_commission_and_owner_payout(client, daraja):
    headers, _, booking_id = create_booking(client)
    booking = client.get("/api/bookings/me", headers=headers).json()[0]
    assert booking["id"] == booking_id
    assert booking["commission_amount"] == "5.00"
    assert booking["owner_payout_amount"] == "45.00"
