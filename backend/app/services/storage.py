import re
import uuid
from pathlib import Path
from typing import Protocol

from fastapi import UploadFile

from app.core.errors import AppError

MAX_UPLOAD_SIZE = 5 * 1024 * 1024
ALLOWED_DOCUMENT_TYPES = {
    "image/jpeg": (".jpg", lambda content: content.startswith(b"\xff\xd8\xff")),
    "image/png": (".png", lambda content: content.startswith(b"\x89PNG\r\n\x1a\n")),
    "application/pdf": (".pdf", lambda content: content.startswith(b"%PDF-")),
}
ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png"}


class Storage(Protocol):
    def save(self, content: bytes, content_type: str, *, public: bool) -> str: ...

    def path(self, storage_key: str, *, public: bool) -> Path: ...

    def delete(self, storage_key: str, *, public: bool) -> None: ...


class LocalStorage:
    def __init__(self) -> None:
        self.base_dir = Path(__file__).resolve().parents[2] / "uploads"

    def save(self, content: bytes, content_type: str, *, public: bool) -> str:
        extension = ALLOWED_DOCUMENT_TYPES[content_type][0]
        storage_key = f"{uuid.uuid4().hex}{extension}"
        destination = self.path(storage_key, public=public)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as file:
            file.write(content)
        return storage_key

    def path(self, storage_key: str, *, public: bool) -> Path:
        if re.fullmatch(r"[0-9a-f]{32}\.(jpg|png|pdf)", storage_key) is None:
            raise ValueError("Invalid generated storage key")
        directory = self.base_dir / ("public" if public else "private")
        return directory / storage_key

    def delete(self, storage_key: str, *, public: bool) -> None:
        self.path(storage_key, public=public).unlink(missing_ok=True)


storage = LocalStorage()


def read_valid_upload(upload: UploadFile, *, photo: bool = False) -> tuple[bytes, str]:
    content_type = upload.content_type or ""
    allowed_types = ALLOWED_PHOTO_TYPES if photo else ALLOWED_DOCUMENT_TYPES.keys()
    if content_type not in allowed_types:
        raise AppError(422, "invalid_file_type", "Only JPG, PNG, and PDF files are allowed")

    content = upload.file.read(MAX_UPLOAD_SIZE + 1)
    if not content:
        raise AppError(422, "empty_file", "Uploaded file is empty")
    if len(content) > MAX_UPLOAD_SIZE:
        raise AppError(413, "file_too_large", "Uploaded files must be 5 MB or smaller")

    _, signature_validator = ALLOWED_DOCUMENT_TYPES[content_type]
    if not signature_validator(content):
        raise AppError(422, "invalid_file_content", "File content does not match its media type")
    return content, content_type
