from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.models import OwnerProfile, User, Vehicle
from app.routers.auth import current_user, require_verified_phone
from app.schemas.fleet import (
    FileUploadResponse,
    OwnerApplicationRequest,
    OwnerApplicationResponse,
    VehicleResponse,
)
from app.services.file_records import persist_upload
from app.services.fleet import apply_as_owner

router = APIRouter(prefix="/api/owners", tags=["owners"])


@router.post("/apply", response_model=OwnerApplicationResponse, status_code=201)
def apply(
    payload: OwnerApplicationRequest,
    user: User = Depends(require_verified_phone),
    db: Session = Depends(get_db),
) -> OwnerApplicationResponse:
    profile = apply_as_owner(db, user, payload)
    return OwnerApplicationResponse.model_validate(profile)


@router.get("/me/vehicles", response_model=list[VehicleResponse])
def my_vehicles(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[VehicleResponse]:
    if db.get(OwnerProfile, user.id) is None:
        raise AppError(403, "owner_profile_required", "An owner application is required")
    vehicles = db.scalars(
        select(Vehicle).where(Vehicle.owner_id == user.id).order_by(Vehicle.created_at.desc())
    ).all()
    return [VehicleResponse.model_validate(vehicle) for vehicle in vehicles]


@router.post("/me/documents", response_model=FileUploadResponse, status_code=201)
def upload_owner_document(
    document_type: Annotated[Literal["id", "selfie"], Form()],
    file: Annotated[UploadFile, File()],
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> FileUploadResponse:
    profile = db.get(OwnerProfile, user.id)
    if profile is None:
        raise AppError(403, "owner_profile_required", "Apply as an owner before uploading documents")

    def link(record) -> None:
        url = f"/api/files/{record.id}"
        if document_type == "id":
            profile.id_doc_url = url
        else:
            profile.selfie_url = url

    record = persist_upload(
        db,
        user,
        file,
        document_type,
        vehicle_id=None,
        link=link,
    )
    return FileUploadResponse(file_id=record.id, download_url=f"/api/files/{record.id}")
