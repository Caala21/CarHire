import base64
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.errors import AppError
from app.models import (
    Booking,
    BookingStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
    PaymentType,
    User,
)

logger = logging.getLogger(__name__)
HTTP_TIMEOUT = 15
PAYMENT_RECONCILE_AFTER_SECONDS = 120


class MpesaGatewayError(Exception):
    pass


_token_lock = threading.Lock()
_cached_token: str | None = None
_token_expires_at = 0.0


def _secret(value) -> str:
    return value.get_secret_value() if value is not None else ""


def _api_base_url() -> str:
    environment = settings.mpesa_env
    return (
        "https://api.safaricom.co.ke"
        if environment == "production"
        else "https://sandbox.safaricom.co.ke"
    )


def _json_response(response: requests.Response) -> dict[str, Any]:
    try:
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise MpesaGatewayError("Daraja request failed") from exc
    if not isinstance(payload, dict):
        raise MpesaGatewayError("Daraja returned an invalid response")
    return payload


def get_oauth_token() -> str:
    global _cached_token, _token_expires_at
    with _token_lock:
        if _cached_token and time.monotonic() < _token_expires_at:
            return _cached_token

        try:
            response = requests.get(
                f"{_api_base_url()}/oauth/v1/generate",
                params={"grant_type": "client_credentials"},
                auth=(_secret(settings.mpesa_consumer_key), _secret(settings.mpesa_consumer_secret)),
                timeout=HTTP_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise MpesaGatewayError("Daraja authentication failed") from exc
        payload = _json_response(response)
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise MpesaGatewayError("Daraja returned no access token")
        try:
            expires_in = max(int(payload.get("expires_in", 3600)), 1)
        except (TypeError, ValueError) as exc:
            raise MpesaGatewayError("Daraja returned an invalid token expiry") from exc
        _cached_token = access_token
        _token_expires_at = time.monotonic() + max(expires_in - 60, 0)
        return access_token


def _timestamp() -> str:
    return datetime.now(ZoneInfo("Africa/Nairobi")).strftime("%Y%m%d%H%M%S")


def _stk_password(timestamp: str) -> str:
    credentials = f"{_secret(settings.mpesa_shortcode)}{_secret(settings.mpesa_passkey)}{timestamp}"
    return base64.b64encode(credentials.encode()).decode()


def _authorized_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    token = get_oauth_token()
    try:
        response = requests.post(
            f"{_api_base_url()}{path}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=HTTP_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise MpesaGatewayError("Daraja request failed") from exc
    return _json_response(response)


def initiate_stk_push(booking: Booking, phone: str) -> dict[str, str]:
    amount = Decimal(booking.deposit_amount)
    if amount <= 0 or amount != amount.to_integral_value():
        raise AppError(409, "invalid_deposit_amount", "M-Pesa deposits must be a positive whole number of shillings")

    timestamp = _timestamp()
    callback_base_url = _secret(settings.mpesa_callback_base_url).rstrip("/")
    payload = {
        "BusinessShortCode": _secret(settings.mpesa_shortcode),
        "Password": _stk_password(timestamp),
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": _secret(settings.mpesa_shortcode),
        "PhoneNumber": phone,
        "CallBackURL": (
            f"{callback_base_url}/api/payments/mpesa/callback/"
            f"{_secret(settings.mpesa_callback_secret)}"
        ),
        "AccountReference": f"Booking{booking.id}",
        "TransactionDesc": f"CarHire booking {booking.id} deposit",
    }
    try:
        response = _authorized_post("/mpesa/stkpush/v1/processrequest", payload)
    except MpesaGatewayError:
        logger.warning("Daraja STK Push request failed for booking_id=%s", booking.id)
        raise
    checkout_id = response.get("CheckoutRequestID")
    merchant_id = response.get("MerchantRequestID")
    if str(response.get("ResponseCode")) != "0" or not checkout_id or not merchant_id:
        logger.warning("Daraja rejected STK Push for booking_id=%s", booking.id)
        raise MpesaGatewayError("Daraja rejected the payment request")
    return {"checkout_request_id": str(checkout_id), "merchant_request_id": str(merchant_id)}


def query_stk_payment(checkout_request_id: str) -> dict[str, Any]:
    timestamp = _timestamp()
    payload = {
        "BusinessShortCode": _secret(settings.mpesa_shortcode),
        "Password": _stk_password(timestamp),
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id,
    }
    return _authorized_post("/mpesa/stkpushquery/v1/query", payload)


def _callback_metadata(callback: dict[str, Any]) -> dict[str, Any]:
    details = callback.get("CallbackMetadata")
    if not isinstance(details, dict):
        return {}
    items = details.get("Item", [])
    if not isinstance(items, list):
        return {}
    return {
        item.get("Name"): item.get("Value")
        for item in items
        if isinstance(item, dict) and isinstance(item.get("Name"), str)
    }


def _payment_for_checkout(db: Session, checkout_request_id: str) -> Payment | None:
    return db.scalar(
        select(Payment)
        .options(joinedload(Payment.booking).joinedload(Booking.vehicle))
        .where(Payment.checkout_request_id == checkout_request_id)
    )


def _complete_payment(
    db: Session,
    payment: Payment,
    result: dict[str, Any],
    callback: dict[str, Any] | None = None,
) -> bool:
    metadata = _callback_metadata(callback or {})
    query_metadata = _callback_metadata(result)
    metadata = {**metadata, **query_metadata}
    amount = metadata.get("Amount")
    receipt = metadata.get("MpesaReceiptNumber") or payment.callback_receipt
    phone = metadata.get("PhoneNumber") or payment.callback_phone
    if amount is None:
        amount = payment.callback_amount
    try:
        received_amount = Decimal(str(amount))
    except (ValueError, TypeError, ArithmeticError):
        return False
    if received_amount != Decimal(payment.amount):
        _fail_payment(db, payment, "M-Pesa payment amount did not match the booking deposit")
        return False
    if not isinstance(receipt, str) or not receipt or phone is None:
        return False
    if str(phone) != payment.mpesa_phone:
        _fail_payment(db, payment, "M-Pesa payment phone did not match the requested phone")
        return False

    payment.status = PaymentStatus.COMPLETED
    payment.mpesa_receipt = receipt
    payment.mpesa_phone = str(phone)
    payment.callback_amount = None
    payment.callback_receipt = None
    payment.callback_phone = None
    payment.paid_at = datetime.now(timezone.utc)
    payment.payout_status = "awaiting"
    payment.booking.status = BookingStatus.CONFIRMED
    payment.booking.deposit_paid = True
    db.commit()
    logger.info("M-Pesa payment completed payment_id=%s booking_id=%s", payment.id, payment.booking_id)
    return True


def _fail_payment(db: Session, payment: Payment, description: str | None) -> None:
    payment.status = PaymentStatus.FAILED
    payment.result_description = (description or "Payment was not completed")[:2000]
    db.commit()
    logger.info("M-Pesa payment failed payment_id=%s", payment.id)


def process_mpesa_callback(db: Session, payload: dict[str, Any]) -> None:
    body = payload.get("Body")
    callback = body.get("stkCallback") if isinstance(body, dict) else None
    if not isinstance(callback, dict):
        return
    checkout_request_id = callback.get("CheckoutRequestID")
    if not isinstance(checkout_request_id, str):
        return
    payment = _payment_for_checkout(db, checkout_request_id)
    if payment is None or payment.status is not PaymentStatus.PENDING:
        return

    if str(callback.get("ResultCode")) == "0":
        metadata = _callback_metadata(callback)
        amount = metadata.get("Amount")
        try:
            payment.callback_amount = Decimal(str(amount)) if amount is not None else None
        except (ValueError, TypeError, ArithmeticError):
            payment.callback_amount = None
        receipt = metadata.get("MpesaReceiptNumber")
        phone = metadata.get("PhoneNumber")
        payment.callback_receipt = receipt if isinstance(receipt, str) else None
        payment.callback_phone = str(phone) if phone is not None else None
        db.commit()

    try:
        result = query_stk_payment(checkout_request_id)
    except MpesaGatewayError:
        logger.warning("Unable to verify M-Pesa callback payment_id=%s", payment.id)
        return

    result_code = result.get("ResultCode")
    callback_code = callback.get("ResultCode")
    if str(result_code) == "0" and str(callback_code) == "0":
        _complete_payment(db, payment, result, callback)
    elif result_code is not None and str(result_code) != "0":
        _fail_payment(db, payment, str(result.get("ResultDesc") or callback.get("ResultDesc") or "Payment failed"))


def list_reconciliation_candidates(db: Session, now: datetime | None = None) -> list[Payment]:
    current_time = now or datetime.now(timezone.utc)
    cutoff = current_time - timedelta(seconds=PAYMENT_RECONCILE_AFTER_SECONDS)
    return db.scalars(
        select(Payment)
        .options(joinedload(Payment.booking).joinedload(Booking.vehicle))
        .where(Payment.status == PaymentStatus.PENDING, Payment.created_at <= cutoff)
        .order_by(Payment.created_at, Payment.id)
    ).unique().all()


def reconcile_payment(db: Session, payment: Payment) -> bool:
    if not payment.checkout_request_id or payment.status is not PaymentStatus.PENDING:
        return False
    try:
        result = query_stk_payment(payment.checkout_request_id)
    except MpesaGatewayError:
        logger.warning("Unable to reconcile M-Pesa payment_id=%s", payment.id)
        return False
    result_code = result.get("ResultCode")
    if str(result_code) == "0":
        return _complete_payment(db, payment, result)
    if result_code is not None:
        _fail_payment(db, payment, str(result.get("ResultDesc") or "Payment failed"))
        return True
    return False


def create_deposit_payment(db: Session, user: User, booking_id: int, phone: str) -> Payment:
    booking = db.scalar(
        select(Booking)
        .options(joinedload(Booking.vehicle))
        .where(Booking.id == booking_id)
        .with_for_update()
    )
    if booking is None or booking.customer_id != user.id:
        raise AppError(404, "booking_not_found", "Booking was not found")
    if user.phone_verified_at is None:
        raise AppError(403, "phone_not_verified", "Phone verification is required")
    if booking.status is not BookingStatus.PENDING:
        raise AppError(409, "booking_not_payable", "This booking is not awaiting payment")
    if booking.expires_at is not None:
        expires_at = booking.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            raise AppError(409, "booking_expired", "This booking has expired")
    active_payment = db.scalar(
        select(Payment.id).where(
            Payment.booking_id == booking.id,
            Payment.status.in_((PaymentStatus.PENDING, PaymentStatus.COMPLETED)),
        )
    )
    if active_payment is not None or booking.deposit_paid:
        raise AppError(409, "payment_exists", "A pending or completed payment already exists for this booking")

    identifiers = initiate_stk_push(booking, phone)
    payment = Payment(
        booking_id=booking.id,
        amount=booking.deposit_amount,
        type=PaymentType.DEPOSIT,
        method=PaymentMethod.MPESA,
        status=PaymentStatus.PENDING,
        mpesa_phone=phone,
        **identifiers,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    logger.info("M-Pesa STK Push started payment_id=%s booking_id=%s", payment.id, booking.id)
    return payment
