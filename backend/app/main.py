import logging
import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import register_error_handlers
from app.routers import admin, assistant, auth, bookings, files, owners, payments, vehicles

app = FastAPI(title=settings.app_name, version="0.1.0")


class CoordinateQueryRedactionFilter(logging.Filter):
    _coordinates = re.compile(r"([?&]near_(?:lat|lng)=)[^&\s]+")
    _callback_secret = re.compile(r"(/api/payments/mpesa/callback/)[^/?\s]+")

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(
                self._callback_secret.sub(
                    r"\1[redacted]",
                    self._coordinates.sub(r"\1[redacted]", value),
                )
                if isinstance(value, str)
                else value
                for value in record.args
            )
        return True


logging.getLogger("uvicorn.access").addFilter(CoordinateQueryRedactionFilter())
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r"^https://[a-zA-Z0-9-]+\.app\.github\.dev$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)
app.include_router(auth.router, prefix="/api")
app.include_router(bookings.router, prefix="/api")
app.include_router(payments.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(admin.api_router, prefix="/api")
app.include_router(owners.router, prefix="/api")
app.include_router(assistant.router, prefix="/api")
app.include_router(vehicles.router, prefix="/api")
app.include_router(vehicles.public_router, prefix="/api")
app.include_router(files.router, prefix="/api")


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}