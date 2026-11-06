from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.core.config import settings
from app.models import (
    Booking,
    BookingStatus,
    OwnerProfile,
    User,
    Vehicle,
    VehicleBlock,
)
from app.schemas.bookings import BookingCreateRequest, VehicleBlockCreateRequest
from app.services.fleet import vehicle_is_public

ACTIVE_BOOKING_STATUSES = (
    BookingStatus.PENDING,
    BookingStatus.CONFIRMED,
    BookingStatus.ACTIVE,
)
BOOKING_HOLD_DURATION = timedelta(minutes=30)
BOOKING_OVERLAP_CONSTRAINT = "excl_bookings_active_vehicle_dates"


def expire_pending_bookings(db: Session, now: datetime | None = None) -> int:
    current_time = now or datetime.now(timezone.utc)
    result = db.execute(
        update(Booking)
        .where(
            Booking.status == BookingStatus.PENDING,
            Booking.deposit_paid.is_(False),
            Booking.expires_at <= current_time,
        )
        .values(status=BookingStatus.CANCELLED)
    )
    expired_count = result.rowcount or 0
    if expired_count:
        db.commit()
    return expired_count


def _overlapping_booking(
    db: Session,
    vehicle_id: int,
    start_date: date,
    end_date: date,
) -> bool:
    return db.scalar(
        select(Booking.id)
        .where(
            Booking.vehicle_id == vehicle_id,
            Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            Booking.start_date < end_date,
            Booking.end_date > start_date,
        )
        .limit(1)
    ) is not None


def _overlapping_block(
    db: Session,
    vehicle_id: int,
    start_date: date,
    end_date: date,
) -> bool:
    return db.scalar(
        select(VehicleBlock.id)
        .where(
            VehicleBlock.vehicle_id == vehicle_id,
            VehicleBlock.start_date < end_date,
            VehicleBlock.end_date > start_date,
        )
        .limit(1)
    ) is not None


def _is_overlap_constraint_error(error: IntegrityError) -> bool:
    original = error.orig
    sqlstate = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
    diagnostics = getattr(original, "diag", None)
    constraint_name = getattr(diagnostics, "constraint_name", None)
    return sqlstate == "23P01" or constraint_name == BOOKING_OVERLAP_CONSTRAINT


def create_booking(
    db: Session,
    user: User,
    payload: BookingCreateRequest,
) -> Booking:
    expire_pending_bookings(db)
    vehicle = db.scalar(
        select(Vehicle).where(Vehicle.id == payload.vehicle_id).with_for_update()
    )
    if vehicle is None or not vehicle_is_public(db, vehicle):
        raise AppError(404, "vehicle_not_found", "Vehicle was not found")

    if _overlapping_booking(db, vehicle.id, payload.start_date, payload.end_date) or _overlapping_block(
        db, vehicle.id, payload.start_date, payload.end_date
    ):
        raise AppError(
            409,
            "vehicle_unavailable",
            "This vehicle is unavailable for some or all of those dates",
        )

    number_of_days = (payload.end_date - payload.start_date).days
    deposit = Decimal(vehicle.deposit_amount)
    total_price = Decimal(vehicle.daily_rate) * number_of_days + deposit
    commission_amount = (
        deposit * settings.commission_percent / Decimal("100")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    booking = Booking(
        customer_id=user.id,
        vehicle_id=vehicle.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=BookingStatus.PENDING,
        total_price=total_price,
        deposit_amount=deposit,
        commission_amount=commission_amount,
        owner_payout_amount=deposit - commission_amount,
        deposit_paid=False,
        expires_at=datetime.now(timezone.utc) + BOOKING_HOLD_DURATION,
    )
    db.add(booking)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if _is_overlap_constraint_error(error):
            raise AppError(
                409,
                "vehicle_unavailable",
                "This vehicle is already booked for some or all of those dates",
            ) from error
        raise
    db.refresh(booking)
    return booking


def list_customer_bookings(db: Session, customer_id: int) -> list[Booking]:
    expire_pending_bookings(db)
    return db.scalars(
        select(Booking)
        .options(joinedload(Booking.vehicle))
        .where(Booking.customer_id == customer_id)
        .order_by(Booking.created_at.desc(), Booking.id.desc())
    ).all()


def list_owner_bookings(db: Session, owner_id: int) -> list[Booking]:
    expire_pending_bookings(db)
    if db.get(OwnerProfile, owner_id) is None:
        raise AppError(403, "owner_profile_required", "An owner application is required")
    return db.scalars(
        select(Booking)
        .join(Vehicle, Booking.vehicle_id == Vehicle.id)
        .options(joinedload(Booking.vehicle))
        .where(Vehicle.owner_id == owner_id)
        .order_by(Booking.created_at.desc(), Booking.id.desc())
    ).all()


def list_all_bookings(db: Session) -> list[Booking]:
    expire_pending_bookings(db)
    return db.scalars(
        select(Booking)
        .options(joinedload(Booking.vehicle))
        .order_by(Booking.created_at.desc(), Booking.id.desc())
    ).all()


def cancel_booking(db: Session, booking_id: int, customer_id: int) -> Booking:
    expire_pending_bookings(db)
    booking = db.scalar(
        select(Booking)
        .options(joinedload(Booking.vehicle))
        .where(Booking.id == booking_id)
    )
    if booking is None or booking.customer_id != customer_id:
        raise AppError(404, "booking_not_found", "Booking was not found")
    if booking.start_date <= date.today():
        raise AppError(409, "booking_cannot_be_cancelled", "Bookings cannot be cancelled on or after their start date")
    if booking.status not in (BookingStatus.PENDING, BookingStatus.CONFIRMED):
        raise AppError(409, "booking_cannot_be_cancelled", "This booking can no longer be cancelled")
    booking.status = BookingStatus.CANCELLED
    db.commit()
    db.refresh(booking)
    return booking


def list_vehicle_bookings(
    db: Session,
    vehicle_id: int,
    start_date: date,
    end_date: date,
) -> list[Booking]:
    expire_pending_bookings(db)
    return db.scalars(
        select(Booking)
        .where(
            Booking.vehicle_id == vehicle_id,
            Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            Booking.start_date < end_date,
            Booking.end_date > start_date,
        )
        .order_by(Booking.start_date, Booking.id)
    ).all()


def list_vehicle_blocks(
    db: Session,
    vehicle_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[VehicleBlock]:
    query = select(VehicleBlock).where(VehicleBlock.vehicle_id == vehicle_id)
    if start_date is not None and end_date is not None:
        query = query.where(
            VehicleBlock.start_date < end_date,
            VehicleBlock.end_date > start_date,
        )
    return db.scalars(query.order_by(VehicleBlock.start_date, VehicleBlock.id)).all()


def create_vehicle_block(
    db: Session,
    vehicle: Vehicle,
    user: User,
    payload: VehicleBlockCreateRequest,
) -> VehicleBlock:
    db.refresh(vehicle, with_for_update=True)
    expire_pending_bookings(db)
    if _overlapping_booking(db, vehicle.id, payload.start_date, payload.end_date):
        raise AppError(
            409,
            "booking_conflict",
            "The requested dates overlap an active booking",
        )
    block = VehicleBlock(
        vehicle_id=vehicle.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason.strip() if payload.reason else None,
        created_by=user.id,
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    return block


def delete_vehicle_block(db: Session, block: VehicleBlock) -> None:
    db.delete(block)
    db.commit()
