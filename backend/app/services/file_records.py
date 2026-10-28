from collections.abc import Callable

from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import StoredFile, User
from app.services.storage import read_valid_upload, storage


def persist_upload(
    db: Session,
    actor: User,
    upload: UploadFile,
    purpose: str,
    *,
    vehicle_id: int | None,
    public: bool = False,
    photo: bool = False,
    link: Callable[[StoredFile], None] | None = None,
) -> StoredFile:
    content, content_type = read_valid_upload(upload, photo=photo)
    if photo and content_type not in {"image/jpeg", "image/png"}:
        raise AppError(422, "invalid_photo_type", "Vehicle photos must be JPG or PNG")
    storage_key = storage.save(content, content_type, public=public)
    record = StoredFile(
        uploader_id=actor.id,
        vehicle_id=vehicle_id,
        purpose=purpose,
        storage_key=storage_key,
        content_type=content_type,
        is_public=public,
    )
    db.add(record)
    try:
        db.flush()
        if link is not None:
            link(record)
        db.commit()
        db.refresh(record)
    except SQLAlchemyError:
        db.rollback()
        storage.delete(storage_key, public=public)
        raise
    return record
