from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.models import User
from app.models import (
    OwnerProfile,
    OwnerVerificationStatus,
    Vehicle,
    VehicleApprovalStatus,
)
from app.routers.auth import require_role
from app.schemas.fleet import (
    AdminVehicleResponse,
    OwnerReviewResponse,
    RejectionRequest,
    VehicleResponse,
)
from app.services.fleet import review_owner, review_vehicle
from app.services.expiry import check_vehicle_expiry, list_expiring_vehicles

router = APIRouter(prefix="/admin", tags=["admin"])
api_router = APIRouter(prefix="/api/admin", tags=["admin"])


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


def _admin_vehicle_response(vehicle: Vehicle) -> AdminVehicleResponse:
    return AdminVehicleResponse(
        **VehicleResponse.model_validate(vehicle).model_dump(),
        logbook_download_url=vehicle.logbook_url,
        insurance_download_url=vehicle.insurance_url,
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
    return [_admin_vehicle_response(vehicle) for vehicle in vehicles]


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
    return _admin_vehicle_response(reviewed)


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
    return _admin_vehicle_response(reviewed)


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
    return _admin_vehicle_response(reviewed)


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
    return [_admin_vehicle_response(vehicle) for vehicle in vehicles]