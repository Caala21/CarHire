import hmac
import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import AppError
from app.models import Booking, Payment, PaymentStatus, User, Vehicle
from app.models.enums import Role
from app.routers.auth import current_user, require_role, require_verified_phone
from app.schemas.payments import (
    AdminPaymentResponse,
    BookingReceiptResponse,
    DepositPaymentRequest,
    PaymentResponse,
    PayoutPaymentResponse,
)
from app.services.mpesa import (
    MpesaGatewayError,
    create_deposit_payment,
    process_mpesa_callback,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["payments"])
DARAJA_ACK = {"ResultCode": 0, "ResultDesc": "Accepted"}


def _vehicle_label(booking: Booking) -> str:
    return f"{booking.vehicle.year} {booking.vehicle.make} {booking.vehicle.model}"


@router.post(
    "/bookings/{booking_id}/pay",
    response_model=PaymentResponse,
    status_code=202,
)
def pay_booking_deposit(
    booking_id: int,
    payload: DepositPaymentRequest,
    user: User = Depends(require_verified_phone),
    db: Session = Depends(get_db),
) -> PaymentResponse:
    try:
        payment = create_deposit_payment(db, user, booking_id, payload.phone)
    except MpesaGatewayError as exc:
        raise AppError(502, "payment_provider_error", "M-Pesa could not start the payment request") from exc
    return PaymentResponse.model_validate(payment)


@router.get("/bookings/{booking_id}/payment", response_model=PaymentResponse)
def get_booking_payment(
    booking_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> PaymentResponse:
    booking = db.get(Booking, booking_id)
    if booking is None or booking.customer_id != user.id:
        raise AppError(404, "booking_not_found", "Booking was not found")
    payment = db.scalar(
        select(Payment)
        .where(Payment.booking_id == booking.id)
        .order_by(Payment.created_at.desc(), Payment.id.desc())
        .limit(1)
    )
    if payment is None:
        raise AppError(404, "payment_not_found", "Payment was not found")
    return PaymentResponse.model_validate(payment)


@router.post("/payments/mpesa/callback/{secret}")
async def mpesa_callback(
    secret: str,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    expected_secret = (
        settings.mpesa_callback_secret.get_secret_value()
        if settings.mpesa_callback_secret is not None
        else ""
    )
    if not expected_secret or not hmac.compare_digest(secret, expected_secret):
        raise AppError(404, "not_found", "Not found")
    try:
        payload = json.loads(await request.body())
        if isinstance(payload, dict):
            process_mpesa_callback(db, payload)
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.warning("Ignoring malformed M-Pesa callback")
    except SQLAlchemyError:
        db.rollback()
        logger.error("Unable to persist M-Pesa callback result")
    return JSONResponse(DARAJA_ACK)


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
def get_payment_status(
    payment_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> PaymentResponse:
    payment = db.scalar(
        select(Payment)
        .options(joinedload(Payment.booking).joinedload(Booking.vehicle))
        .where(Payment.id == payment_id)
    )
    if payment is None:
        raise AppError(404, "payment_not_found", "Payment was not found")
    is_allowed = (
        user.role is Role.ADMIN
        or payment.booking.customer_id == user.id
        or payment.booking.vehicle.owner_id == user.id
    )
    if not is_allowed:
        raise AppError(404, "payment_not_found", "Payment was not found")
    return PaymentResponse.model_validate(payment)


@router.get("/bookings/{booking_id}/receipt", response_model=BookingReceiptResponse)
def get_booking_receipt(
    booking_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> BookingReceiptResponse:
    booking = db.scalar(
        select(Booking)
        .options(joinedload(Booking.vehicle))
        .where(Booking.id == booking_id)
    )
    if booking is None:
        raise AppError(404, "booking_not_found", "Booking was not found")
    if (
        user.role is not Role.ADMIN
        and booking.customer_id != user.id
        and booking.vehicle.owner_id != user.id
    ):
        raise AppError(404, "booking_not_found", "Booking was not found")
    payment = db.scalar(
        select(Payment).where(
            Payment.booking_id == booking.id,
            Payment.status == PaymentStatus.COMPLETED,
            Payment.mpesa_receipt.is_not(None),
        ).order_by(Payment.paid_at.desc(), Payment.id.desc())
    )
    if payment is None or payment.paid_at is None or payment.mpesa_receipt is None:
        raise AppError(404, "receipt_not_found", "A payment receipt was not found")
    return BookingReceiptResponse(
        booking_id=booking.id,
        vehicle=_vehicle_label(booking),
        start_date=booking.start_date,
        end_date=booking.end_date,
        amount=payment.amount,
        mpesa_receipt=payment.mpesa_receipt,
        paid_at=payment.paid_at,
    )


@router.get("/admin/payments", response_model=list[AdminPaymentResponse])
def admin_payments(
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> list[AdminPaymentResponse]:
    payments = db.scalars(
        select(Payment)
        .options(joinedload(Payment.booking).joinedload(Booking.vehicle))
        .order_by(Payment.created_at.desc(), Payment.id.desc())
        .limit(500)
    ).unique().all()
    return [
        AdminPaymentResponse(
            id=payment.id,
            booking_id=payment.booking_id,
            vehicle=_vehicle_label(payment.booking),
            amount=payment.amount,
            mpesa_receipt=payment.mpesa_receipt,
            status=payment.status,
            payout_status=payment.payout_status,
            owner_payout_amount=payment.booking.owner_payout_amount,
            commission_amount=payment.booking.commission_amount,
            created_at=payment.created_at,
        )
        for payment in payments
    ]


@router.get("/admin/payments/payouts", response_model=list[PayoutPaymentResponse])
def admin_payments_awaiting_payout(
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> list[PayoutPaymentResponse]:
    rows = db.execute(
        select(Payment, Booking, Vehicle, User.full_name)
        .join(Booking, Payment.booking_id == Booking.id)
        .join(Vehicle, Booking.vehicle_id == Vehicle.id)
        .outerjoin(User, Vehicle.owner_id == User.id)
        .where(Payment.status == PaymentStatus.COMPLETED, Payment.payout_status == "awaiting")
        .order_by(Payment.paid_at, Payment.id)
    ).all()
    return [
        PayoutPaymentResponse(
            id=payment.id,
            booking_id=booking.id,
            vehicle=f"{vehicle.year} {vehicle.make} {vehicle.model}",
            amount=payment.amount,
            mpesa_receipt=payment.mpesa_receipt,
            status=payment.status,
            payout_status=payment.payout_status,
            owner_payout_amount=booking.owner_payout_amount,
            commission_amount=booking.commission_amount,
            created_at=payment.created_at,
            owner_id=vehicle.owner_id,
            owner_name=owner_name,
        )
        for payment, booking, vehicle, owner_name in rows
    ]
