from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.models import OwnerProfile, Role, StoredFile, User, Vehicle
from app.routers.auth import current_user
from app.services.storage import storage

router = APIRouter(prefix="/api", tags=["files"])


@router.get("/files/{file_id}")
def download_private_file(
    file_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    record = db.get(StoredFile, file_id)
    if record is None or record.is_public:
        raise AppError(404, "file_not_found", "File was not found")

    permitted = user.role is Role.ADMIN
    if not permitted and record.vehicle_id is not None and user.role is Role.OWNER:
        vehicle = db.get(Vehicle, record.vehicle_id)
        permitted = vehicle is not None and vehicle.owner_id == user.id
    if (
        not permitted
        and record.purpose in {"id", "selfie"}
        and record.uploader_id == user.id
        and db.get(OwnerProfile, user.id) is not None
    ):
        permitted = True
    if not permitted:
        raise AppError(403, "forbidden", "You cannot download this file")

    path = storage.path(record.storage_key, public=False)
    if not path.is_file():
        raise AppError(404, "file_not_found", "File was not found")
    return FileResponse(
        path,
        media_type=record.content_type,
        filename=f"document-{record.id}",
    )
