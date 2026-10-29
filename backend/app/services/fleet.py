from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import (
    AuditLog,
    OwnerProfile,
    OwnerVerificationStatus,
    Role,
    User,
    Vehicle,
    VehicleApprovalStatus,
)
from app.schemas.fleet import OwnerApplicationRequest, VehicleCreateRequest, VehiclePatchRequest


def apply_as_owner(db: Session, user: User, payload: OwnerApplicationRequest) -> OwnerProfile:
    if user.role is not Role.CUSTOMER:
        raise AppError(409, "role_not_eligible", "Only customer accounts can apply to become owners")
    if db.get(OwnerProfile, user.id) is not None:
        raise AppError(409, "owner_application_exists", "An owner application already exists")

    profile = OwnerProfile(
        user_id=user.id,
        national_id=payload.national_id.strip(),
        kra_pin=payload.kra_pin.strip().upper(),
        payout_phone=payload.payout_phone,
        verification_status=OwnerVerificationStatus.PENDING,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def review_owner(
    db: Session,
    profile: OwnerProfile,
    actor: User,
    *,
    approved: bool,
    reason: str | None = None,
) -> OwnerProfile:
    if profile.verification_status is not OwnerVerificationStatus.PENDING:
        raise AppError(409, "owner_application_not_pending", "Owner application is not pending")
    if approved and (profile.id_doc_url is None or profile.selfie_url is None):
        raise AppError(409, "owner_documents_required", "Owner ID and selfie documents are required")

    now = datetime.now(timezone.utc)
    profile.verification_status = (
        OwnerVerificationStatus.APPROVED if approved else OwnerVerificationStatus.REJECTED
    )
    profile.rejection_reason = None if approved else reason
    profile.reviewed_by = actor.id
    profile.reviewed_at = now
    if approved:
        profile.user.role = Role.OWNER
    db.add(
        AuditLog(
            actor_id=actor.id,
            action="approve" if approved else "reject",
            target_type="owner",
            target_id=profile.user_id,
            reason=reason,
        )
    )
    db.commit()
    db.refresh(profile)
    return profile


def create_vehicle(db: Session, actor: User, payload: VehicleCreateRequest) -> Vehicle:
    if actor.role is Role.OWNER:
        profile = db.get(OwnerProfile, actor.id)
        if profile is None or profile.verification_status is not OwnerVerificationStatus.APPROVED:
            raise AppError(403, "owner_not_approved", "An approved owner profile is required")
        owner_id = actor.id
        approval_status = VehicleApprovalStatus.PENDING
    elif actor.role is Role.CUSTOMER:
        profile = db.get(OwnerProfile, actor.id)
        if profile is None or profile.verification_status is not OwnerVerificationStatus.PENDING:
            raise AppError(403, "owner_application_required", "A pending owner application is required")
        owner_id = actor.id
        approval_status = VehicleApprovalStatus.PENDING
    elif actor.role in (Role.STAFF, Role.ADMIN):
        owner_id = None
        approval_status = VehicleApprovalStatus.APPROVED
    else:
        raise AppError(403, "forbidden", "Only approved owners, staff, and admins can create vehicles")

    vehicle = Vehicle(
        owner_id=owner_id,
        make=payload.make,
        model=payload.model,
        year=payload.year,
        plate=payload.plate.strip().upper(),
        chassis_number=payload.chassis_number.strip(),
        seats=payload.seats,
        transmission=payload.transmission,
        fuel_type=payload.fuel_type,
        daily_rate=payload.daily_rate,
        deposit_amount=payload.deposit_amount,
        insurance_expiry=payload.insurance_expiry,
        inspection_expiry=payload.inspection_expiry,
        location=payload.location.strip(),
        approval_status=approval_status,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


VEHICLE_KEY_FIELDS = {"plate", "chassis_number"}


def update_vehicle(
    db: Session,
    vehicle: Vehicle,
    actor: User,
    payload: VehiclePatchRequest,
) -> Vehicle:
    if actor.role is Role.OWNER:
        if vehicle.owner_id != actor.id:
            raise AppError(403, "forbidden", "You can only edit your own vehicles")
        profile = db.get(OwnerProfile, actor.id)
        if profile is None or profile.verification_status is not OwnerVerificationStatus.APPROVED:
            raise AppError(403, "owner_not_approved", "An approved owner profile is required")
    elif actor.role not in (Role.STAFF, Role.ADMIN):
        raise AppError(403, "forbidden", "You do not have permission to edit vehicles")

    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    if actor.role is Role.OWNER and VEHICLE_KEY_FIELDS.intersection(updates):
        vehicle.approval_status = VehicleApprovalStatus.PENDING
        vehicle.rejection_reason = None
    for field, value in updates.items():
        setattr(vehicle, field, value)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def public_vehicle_query(
    *,
    make: str | None = None,
    seats: int | None = None,
    transmission: str | None = None,
    fuel_type: str | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    location: str | None = None,
):
    query = (
        select(Vehicle)
        .outerjoin(OwnerProfile, Vehicle.owner_id == OwnerProfile.user_id)
        .where(
            Vehicle.approval_status == VehicleApprovalStatus.APPROVED,
            Vehicle.insurance_url.is_not(None),
            Vehicle.insurance_expiry >= date.today(),
            Vehicle.inspection_expiry >= date.today(),
            or_(
                Vehicle.owner_id.is_(None),
                OwnerProfile.verification_status == OwnerVerificationStatus.APPROVED,
            ),
        )
    )
    if make:
        query = query.where(Vehicle.make.ilike(f"%{make}%"))
    if seats is not None:
        query = query.where(Vehicle.seats == seats)
    if transmission:
        query = query.where(Vehicle.transmission.ilike(transmission))
    if fuel_type:
        query = query.where(Vehicle.fuel_type.ilike(fuel_type))
    if min_price is not None:
        query = query.where(Vehicle.daily_rate >= min_price)
    if max_price is not None:
        query = query.where(Vehicle.daily_rate <= max_price)
    if location:
        query = query.where(Vehicle.location.ilike(f"%{location}%"))
    return query


def vehicle_is_public(db: Session, vehicle: Vehicle) -> bool:
    if (
        vehicle.approval_status is not VehicleApprovalStatus.APPROVED
        or vehicle.insurance_url is None
        or vehicle.insurance_expiry is None
        or vehicle.insurance_expiry < date.today()
        or vehicle.inspection_expiry is None
        or vehicle.inspection_expiry < date.today()
    ):
        return False
    if vehicle.owner_id is None:
        return True
    profile = db.get(OwnerProfile, vehicle.owner_id)
    return profile is not None and profile.verification_status is OwnerVerificationStatus.APPROVED


def review_vehicle(
    db: Session,
    vehicle: Vehicle,
    actor: User,
    action: VehicleApprovalStatus,
    reason: str | None = None,
) -> Vehicle:
    if action in (VehicleApprovalStatus.APPROVED, VehicleApprovalStatus.REJECTED):
        if vehicle.approval_status is not VehicleApprovalStatus.PENDING:
            raise AppError(409, "vehicle_not_pending", "Vehicle is not pending review")
    if action is VehicleApprovalStatus.APPROVED:
        if (
            vehicle.chassis_number is None
            or vehicle.logbook_url is None
            or vehicle.insurance_url is None
            or vehicle.insurance_expiry is None
            or vehicle.inspection_expiry is None
            or vehicle.insurance_expiry < date.today()
            or vehicle.inspection_expiry < date.today()
        ):
            raise AppError(409, "vehicle_documents_required", "Valid vehicle documents and expiries are required")
        if vehicle.owner_id is not None:
            owner_profile = db.get(OwnerProfile, vehicle.owner_id)
            if (
                owner_profile is None
                or owner_profile.verification_status is not OwnerVerificationStatus.APPROVED
            ):
                raise AppError(409, "owner_not_approved", "The vehicle owner must be approved first")
    vehicle.approval_status = action
    vehicle.rejection_reason = reason if action is VehicleApprovalStatus.REJECTED else None
    db.add(
        AuditLog(
            actor_id=actor.id,
            action=action.value,
            target_type="vehicle",
            target_id=vehicle.id,
            reason=reason,
        )
    )
    db.commit()
    db.refresh(vehicle)
    return vehicle
