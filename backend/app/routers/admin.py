from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.models import AuditLog, StoredFile, User
from app.models import (
    OwnerProfile,
    OwnerVerificationStatus,
    Vehicle,
    VehicleApprovalStatus,
)
from app.routers.auth import require_role
from app.schemas.fleet import (
    AdminDashboardResponse,
    AdminOwnerDetailResponse,
    AdminVehicleResponse,
    AuditTrailResponse,
    OwnerReviewResponse,
    RejectionRequest,
    VehicleResponse,
)
from app.services.fleet import review_owner, review_vehicle
from app.services.expiry import check_vehicle_expiry, list_expiring_vehicles
from app.services.storage import storage

router = APIRouter(prefix="/admin", tags=["admin"])
api_router = APIRouter(prefix="/admin", tags=["admin"])


class ExpiryCheckResponse(BaseModel):
    suspended_count: int
    vehicle_ids: list[int]


def _owner_response(profile: OwnerProfile) -> OwnerReviewResponse:
    return OwnerReviewResponse(
        user_id=profile.user_id,
        full_name=profile.user.full_name,
        email=profile.user.email,
        phone=profile.user.phone,
        verification_status=profile.verification_status,
        rejection_reason=profile.rejection_reason,
        reviewed_at=profile.reviewed_at,
        created_at=profile.created_at,
        id_document_download_url=profile.id_doc_url,
        selfie_document_download_url=profile.selfie_url,
    )


def _admin_vehicle_response(vehicle: Vehicle, db: Session) -> AdminVehicleResponse:
    owner = db.get(User, vehicle.owner_id) if vehicle.owner_id is not None else None
    owner_profile = db.get(OwnerProfile, vehicle.owner_id) if vehicle.owner_id is not None else None
    return AdminVehicleResponse(
        **VehicleResponse.model_validate(vehicle).model_dump(),
        logbook_download_url=vehicle.logbook_url,
        insurance_download_url=vehicle.insurance_url,
        owner_name=owner.full_name if owner is not None else None,
        owner_id=vehicle.owner_id,
        owner_id_document_download_url=(
            owner_profile.id_doc_url if owner_profile is not None else None
        ),
        owner_verification_status=(
            owner_profile.verification_status if owner_profile is not None else None
        ),
    )


@router.get("/ping")
def admin_ping(user: User = Depends(require_role("admin"))) -> dict[str, str]:
    return {"message": "Admin access granted"}


@api_router.get("/owners", response_model=list[OwnerReviewResponse])
def list_owner_applications(
    status: OwnerVerificationStatus = Query(default=OwnerVerificationStatus.PENDING),
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> list[OwnerReviewResponse]:
    profiles = db.scalars(
        select(OwnerProfile)
        .where(OwnerProfile.verification_status == status)
        .order_by(OwnerProfile.created_at)
    ).all()
    return [_owner_response(profile) for profile in profiles]


@api_router.get("/dashboard", response_model=AdminDashboardResponse)
def admin_dashboard(
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminDashboardResponse:
    today = datetime.now(timezone.utc).date()
    start_of_day = datetime.combine(today, time.min, tzinfo=timezone.utc)
    expiry_deadline = today + timedelta(days=14)
    insurance_due = db.scalar(
        select(func.count()).select_from(Vehicle).where(
            Vehicle.approval_status == VehicleApprovalStatus.APPROVED,
            Vehicle.insurance_expiry.between(today, expiry_deadline),
        )
    ) or 0
    inspection_due = db.scalar(
        select(func.count()).select_from(Vehicle).where(
            Vehicle.approval_status == VehicleApprovalStatus.APPROVED,
            Vehicle.inspection_expiry.between(today, expiry_deadline),
        )
    ) or 0
    return AdminDashboardResponse(
        pending_owners=db.scalar(
            select(func.count()).select_from(OwnerProfile).where(
                OwnerProfile.verification_status == OwnerVerificationStatus.PENDING
            )
        )
        or 0,
        pending_vehicles=db.scalar(
            select(func.count()).select_from(Vehicle).where(
                Vehicle.approval_status == VehicleApprovalStatus.PENDING
            )
        )
        or 0,
        approved_today=db.scalar(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.action == "approve",
                AuditLog.created_at >= start_of_day,
            )
        )
        or 0,
        expiring_documents=insurance_due + inspection_due,
    )


@api_router.get("/audit", response_model=list[AuditTrailResponse])
def admin_audit_trail(
    limit: int = Query(default=30, ge=1, le=100),
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> list[AuditTrailResponse]:
    records = db.execute(
        select(AuditLog, User.full_name)
        .outerjoin(User, AuditLog.actor_id == User.id)
        .where(AuditLog.action.in_(("approve", "reject", "suspend")))
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
    ).all()
    return [
        AuditTrailResponse(
            id=record.id,
            action=record.action,
            target_type=record.target_type,
            target_id=record.target_id,
            actor_name=actor_name,
            reason=record.reason,
            created_at=record.created_at,
        )
        for record, actor_name in records
    ]


@api_router.get("/owners/{user_id}", response_model=AdminOwnerDetailResponse)
def get_owner_application(
    user_id: int,
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminOwnerDetailResponse:
    profile = db.get(OwnerProfile, user_id)
    if profile is None:
        raise AppError(404, "owner_application_not_found", "Owner application was not found")
    return AdminOwnerDetailResponse(
        **_owner_response(profile).model_dump(),
        national_id=profile.national_id,
        kra_pin=profile.kra_pin,
        payout_phone=profile.payout_phone,
    )


@api_router.post("/owners/{user_id}/approve", response_model=OwnerReviewResponse)
def approve_owner(
    user_id: int,
    actor: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> OwnerReviewResponse:
    profile = db.get(OwnerProfile, user_id)
    if profile is None:
        raise AppError(404, "owner_application_not_found", "Owner application was not found")
    profile = review_owner(db, profile, actor, approved=True)
    return _owner_response(profile)


@api_router.post("/owners/{user_id}/reject", response_model=OwnerReviewResponse)
def reject_owner(
    user_id: int,
    payload: RejectionRequest,
    actor: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> OwnerReviewResponse:
    profile = db.get(OwnerProfile, user_id)
    if profile is None:
        raise AppError(404, "owner_application_not_found", "Owner application was not found")
    profile = review_owner(db, profile, actor, approved=False, reason=payload.reason)
    return _owner_response(profile)


@api_router.get("/vehicles", response_model=list[AdminVehicleResponse])
def list_vehicle_applications(
    status: VehicleApprovalStatus = Query(default=VehicleApprovalStatus.PENDING),
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> list[AdminVehicleResponse]:
    vehicles = db.scalars(
        select(Vehicle)
        .where(Vehicle.approval_status == status)
        .order_by(Vehicle.created_at)
    ).all()
    return [_admin_vehicle_response(vehicle, db) for vehicle in vehicles]


@api_router.post("/vehicles/{vehicle_id}/approve", response_model=AdminVehicleResponse)
def approve_vehicle(
    vehicle_id: int,
    actor: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminVehicleResponse:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise AppError(404, "vehicle_not_found", "Vehicle was not found")
    reviewed = review_vehicle(db, vehicle, actor, VehicleApprovalStatus.APPROVED)
    return _admin_vehicle_response(reviewed, db)


@api_router.post("/vehicles/{vehicle_id}/reject", response_model=AdminVehicleResponse)
def reject_vehicle(
    vehicle_id: int,
    payload: RejectionRequest,
    actor: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminVehicleResponse:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise AppError(404, "vehicle_not_found", "Vehicle was not found")
    reviewed = review_vehicle(
        db,
        vehicle,
        actor,
        VehicleApprovalStatus.REJECTED,
        payload.reason,
    )
    return _admin_vehicle_response(reviewed, db)


@api_router.post("/vehicles/{vehicle_id}/suspend", response_model=AdminVehicleResponse)
def suspend_vehicle(
    vehicle_id: int,
    actor: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminVehicleResponse:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise AppError(404, "vehicle_not_found", "Vehicle was not found")
    reviewed = review_vehicle(db, vehicle, actor, VehicleApprovalStatus.SUSPENDED)
    return _admin_vehicle_response(reviewed, db)


@api_router.post("/jobs/check-expiry", response_model=ExpiryCheckResponse)
def run_expiry_check(
    actor: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> ExpiryCheckResponse:
    vehicle_ids = check_vehicle_expiry(db, actor_id=actor.id)
    return ExpiryCheckResponse(suspended_count=len(vehicle_ids), vehicle_ids=vehicle_ids)


@api_router.get("/vehicles/expiring", response_model=list[AdminVehicleResponse])
def expiring_vehicles(
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> list[AdminVehicleResponse]:
    vehicles = list_expiring_vehicles(db)
    return [_admin_vehicle_response(vehicle, db) for vehicle in vehicles]


@api_router.get("/vehicle-photos/{file_id}")
def get_admin_vehicle_photo(
    file_id: int,
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> FileResponse:
    record = db.get(StoredFile, file_id)
    if (
        record is None
        or not record.is_public
        or record.purpose != "photo"
        or record.vehicle_id is None
    ):
        raise AppError(404, "file_not_found", "File was not found")
    path = storage.path(record.storage_key, public=True)
    if not path.is_file():
        raise AppError(404, "file_not_found", "File was not found")
    return FileResponse(path, media_type=record.content_type)