from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import User
from app.routers.auth import current_user, require_verified_phone
from app.schemas.bookings import BookingCreateRequest, BookingResponse
from app.services.bookings import (
    cancel_booking,
    create_booking,
    list_customer_bookings,
)

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingResponse, status_code=201)
def create(
    payload: BookingCreateRequest,
    user: User = Depends(require_verified_phone),
    db: Session = Depends(get_db),
) -> BookingResponse:
    return BookingResponse.model_validate(create_booking(db, user, payload))


@router.get("/me", response_model=list[BookingResponse])
def my_bookings(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[BookingResponse]:
    return [
        BookingResponse.model_validate(booking)
        for booking in list_customer_bookings(db, user.id)
    ]


@router.post("/{booking_id}/cancel", response_model=BookingResponse)
def cancel(
    booking_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> BookingResponse:
    booking = cancel_booking(db, booking_id, user.id)
    return BookingResponse.model_validate(booking)
