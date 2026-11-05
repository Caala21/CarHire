from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.models import (
    Booking,
    BookingStatus,
    OwnerProfile,
    Role,
    StoredFile,
    User,
    Vehicle,
    VehicleApprovalStatus,
    VehicleBlock,
)
from app.routers.auth import current_user
from app.schemas.bookings import (
    AvailabilityRange,
    AvailabilityResponse,
    VehicleBlockCreateRequest,
    VehicleBlockResponse,
)
from app.schemas.fleet import (
    FileUploadResponse,
    VehicleCreateRequest,
    VehiclePageResponse,
    VehiclePatchRequest,
    VehicleResponse,
)
from app.services.bookings import (
    create_vehicle_block,
    delete_vehicle_block,
    expire_pending_bookings,
    list_vehicle_blocks,
    list_vehicle_bookings,
)
from app.services.file_records import persist_upload
from app.services.fleet import (
    create_vehicle,
    public_vehicle_query,
    update_vehicle,
    vehicle_is_public,
)
from app.services.storage import storage

router = APIRouter(prefix="/vehicles", tags=["vehicles"])
public_router = APIRouter(prefix="/public", tags=["public"])
ACTIVE_BOOKING_STATUSES = (
    BookingStatus.PENDING,
    BookingStatus.CONFIRMED,
    BookingStatus.ACTIVE,
)


def _get_vehicle(db: Session, vehicle_id: int) -> Vehicle:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise AppError(404, "vehicle_not_found", "Vehicle was not found")
    return vehicle


def _can_manage_documents(db: Session, vehicle: Vehicle, user: User) -> None:
    if user.role in (Role.STAFF, Role.ADMIN):
        return
    if user.role in (Role.CUSTOMER, Role.OWNER) and vehicle.owner_id == user.id:
        profile = db.get(OwnerProfile, user.id)
        if profile is not None and profile.verification_status.value in {"pending", "approved"}:
            return
    raise AppError(403, "forbidden", "You can only manage documents for your own vehicles")


def _can_manage_blocks(vehicle: Vehicle, user: User) -> None:
    if user.role is Role.ADMIN:
        return
    if user.role is Role.OWNER and vehicle.owner_id == user.id:
        return
    raise AppError(403, "forbidden", "You can only manage availability for your own vehicles")


@router.get("", response_model=VehiclePageResponse)
def list_vehicles(
    make: str | None = None,
    model: str | None = None,
    seats: int | None = Query(default=None, ge=1, le=100),
    transmission: str | None = None,
    fuel_type: str | None = None,
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    location: str | None = None,
    available_from: date | None = None,
    available_to: date | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> VehiclePageResponse:
    if (available_from is None) != (available_to is None):
        raise AppError(422, "invalid_date_range", "Both available_from and available_to are required")
    if available_from is not None and available_to is not None:
        if available_to <= available_from:
            raise AppError(422, "invalid_date_range", "available_to must be after available_from")
        expire_pending_bookings(db)
    query = public_vehicle_query(
        make=make,
        model=model,
        seats=seats,
        transmission=transmission,
        fuel_type=fuel_type,
        min_price=min_price,
        max_price=max_price,
        location=location,
    )
    if available_from is not None and available_to is not None:
        query = query.where(
            ~select(Booking.id).where(
                Booking.vehicle_id == Vehicle.id,
                Booking.status.in_(ACTIVE_BOOKING_STATUSES),
                Booking.start_date < available_to,
                Booking.end_date > available_from,
            ).exists(),
            ~select(VehicleBlock.id).where(
                VehicleBlock.vehicle_id == Vehicle.id,
                VehicleBlock.start_date < available_to,
                VehicleBlock.end_date > available_from,
            ).exists(),
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    vehicles = db.scalars(
        query.order_by(Vehicle.created_at.desc(), Vehicle.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return VehiclePageResponse(
        items=[VehicleResponse.model_validate(vehicle) for vehicle in vehicles],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=VehicleResponse, status_code=201)
def create(
    payload: VehicleCreateRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> VehicleResponse:
    return VehicleResponse.model_validate(create_vehicle(db, user, payload))


@router.get("/{vehicle_id}", response_model=VehicleResponse)
def get_public_vehicle(vehicle_id: int, db: Session = Depends(get_db)) -> VehicleResponse:
    vehicle = _get_vehicle(db, vehicle_id)
    if not vehicle_is_public(db, vehicle):
        raise AppError(404, "vehicle_not_found", "Vehicle was not found")
    return VehicleResponse.model_validate(vehicle)


@router.get("/{vehicle_id}/availability", response_model=AvailabilityResponse)
def vehicle_availability(
    vehicle_id: int,
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
    db: Session = Depends(get_db),
) -> AvailabilityResponse:
    vehicle = _get_vehicle(db, vehicle_id)
    if not vehicle_is_public(db, vehicle):
        raise AppError(404, "vehicle_not_found", "Vehicle was not found")
    if to_date <= from_date:
        raise AppError(422, "invalid_date_range", "The end of the availability range must be after its start")
    bookings = list_vehicle_bookings(db, vehicle_id, from_date, to_date)
    blocks = list_vehicle_blocks(db, vehicle_id, from_date, to_date)
    return AvailabilityResponse(
        vehicle_id=vehicle_id,
        blocked_ranges=sorted([
            AvailabilityRange(
                start_date=max(booking.start_date, from_date),
                end_date=min(booking.end_date, to_date),
            )
            for booking in bookings
        ] + [
            AvailabilityRange(
                start_date=max(block.start_date, from_date),
                end_date=min(block.end_date, to_date),
            )
            for block in blocks
        ], key=lambda blocked_range: (blocked_range.start_date, blocked_range.end_date)),
    )


@router.get("/{vehicle_id}/blocks", response_model=list[VehicleBlockResponse])
def get_vehicle_blocks(
    vehicle_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[VehicleBlockResponse]:
    vehicle = _get_vehicle(db, vehicle_id)
    _can_manage_blocks(vehicle, user)
    return [
        VehicleBlockResponse.model_validate(block)
        for block in list_vehicle_blocks(db, vehicle_id)
    ]


@router.post("/{vehicle_id}/blocks", response_model=VehicleBlockResponse, status_code=201)
def post_vehicle_block(
    vehicle_id: int,
    payload: VehicleBlockCreateRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> VehicleBlockResponse:
    vehicle = _get_vehicle(db, vehicle_id)
    _can_manage_blocks(vehicle, user)
    block = create_vehicle_block(db, vehicle, user, payload)
    return VehicleBlockResponse.model_validate(block)


@router.delete("/{vehicle_id}/blocks/{block_id}", status_code=204)
def remove_vehicle_block(
    vehicle_id: int,
    block_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> None:
    vehicle = _get_vehicle(db, vehicle_id)
    _can_manage_blocks(vehicle, user)
    block = db.get(VehicleBlock, block_id)
    if block is None or block.vehicle_id != vehicle.id:
        raise AppError(404, "vehicle_block_not_found", "Availability block was not found")
    delete_vehicle_block(db, block)


@router.patch("/{vehicle_id}", response_model=VehicleResponse)
def patch_vehicle(
    vehicle_id: int,
    payload: VehiclePatchRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> VehicleResponse:
    vehicle = _get_vehicle(db, vehicle_id)
    updated = update_vehicle(db, vehicle, user, payload)
    return VehicleResponse.model_validate(updated)


@router.post("/{vehicle_id}/documents", response_model=FileUploadResponse, status_code=201)
def upload_vehicle_document(
    vehicle_id: int,
    document_type: Annotated[Literal["logbook", "insurance"], Form()],
    file: Annotated[UploadFile, File()],
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> FileUploadResponse:
    vehicle = _get_vehicle(db, vehicle_id)
    _can_manage_documents(db, vehicle, user)

    def link(record: StoredFile) -> None:
        url = f"/api/files/{record.id}"
        if document_type == "logbook":
            vehicle.logbook_url = url
        else:
            vehicle.insurance_url = url
        vehicle.approval_status = VehicleApprovalStatus.PENDING
        vehicle.rejection_reason = None

    record = persist_upload(
        db,
        user,
        file,
        document_type,
        vehicle_id=vehicle.id,
        link=link,
    )
    return FileUploadResponse(file_id=record.id, download_url=f"/api/files/{record.id}")


@router.post("/{vehicle_id}/photos", response_model=FileUploadResponse, status_code=201)
def upload_vehicle_photo(
    vehicle_id: int,
    file: Annotated[UploadFile, File()],
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> FileUploadResponse:
    vehicle = _get_vehicle(db, vehicle_id)
    _can_manage_documents(db, vehicle, user)
    db.refresh(vehicle, with_for_update=True)
    if len(vehicle.photos or []) >= 8:
        raise AppError(409, "photo_limit_reached", "A vehicle may have at most 8 photos")

    def link(record: StoredFile) -> None:
        photo_url = f"/api/public/vehicle-photos/{record.id}"
        vehicle.photos = [*(vehicle.photos or []), photo_url]

    record = persist_upload(
        db,
        user,
        file,
        "photo",
        vehicle_id=vehicle.id,
        public=True,
        photo=True,
        link=link,
    )
    return FileUploadResponse(
        file_id=record.id,
        download_url=f"/api/public/vehicle-photos/{record.id}",
    )


@public_router.get("/vehicle-photos/{file_id}")
def get_public_vehicle_photo(file_id: int, db: Session = Depends(get_db)) -> FileResponse:
    record = db.get(StoredFile, file_id)
    if record is None or not record.is_public or record.purpose != "photo" or record.vehicle_id is None:
        raise AppError(404, "file_not_found", "File was not found")
    vehicle = db.get(Vehicle, record.vehicle_id)
    if vehicle is None or not vehicle_is_public(db, vehicle):
        raise AppError(404, "file_not_found", "File was not found")
    path = storage.path(record.storage_key, public=True)
    if not path.is_file():
        raise AppError(404, "file_not_found", "File was not found")
    return FileResponse(path, media_type=record.content_type)
