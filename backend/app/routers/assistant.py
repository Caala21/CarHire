from collections import deque
from threading import Lock
from time import monotonic

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.schemas.fleet import (
    AssistantSearchRequest,
    AssistantSearchResponse,
    AssistantVehicleResponse,
)
from app.services.assistant import assistant_search

router = APIRouter(prefix="/assistant", tags=["assistant"])
RATE_LIMIT = 10
RATE_WINDOW_SECONDS = 60
_request_times: dict[str, deque[float]] = {}
_last_prune = 0.0
_rate_limit_lock = Lock()


def _check_rate_limit(client_ip: str) -> None:
    global _last_prune
    now = monotonic()
    cutoff = now - RATE_WINDOW_SECONDS
    with _rate_limit_lock:
        if now - _last_prune >= RATE_WINDOW_SECONDS:
            for ip, timestamps in list(_request_times.items()):
                while timestamps and timestamps[0] <= cutoff:
                    timestamps.popleft()
                if not timestamps:
                    del _request_times[ip]
            _last_prune = now

        timestamps = _request_times.setdefault(client_ip, deque())
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()
        if len(timestamps) >= RATE_LIMIT:
            raise AppError(429, "assistant_rate_limited", "Too many search requests. Please try again shortly.")
        timestamps.append(now)


@router.post("/search", response_model=AssistantSearchResponse)
def search(
    payload: AssistantSearchRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> AssistantSearchResponse:
    _check_rate_limit(request.client.host if request.client else "unknown")
    reply, filters, vehicles = assistant_search(db, payload.message)
    return AssistantSearchResponse(
        reply=reply,
        filters=filters,
        vehicles=[AssistantVehicleResponse.model_validate(vehicle, from_attributes=True) for vehicle in vehicles],
    )
