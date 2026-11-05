import json
import threading
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.models import GeocodeCache

_request_lock = threading.Lock()
_last_request_at = 0.0


def _area_name(address: dict) -> str:
    neighbourhood = (
        address.get("neighbourhood")
        or address.get("suburb")
        or address.get("quarter")
        or address.get("city_district")
    )
    city = address.get("city") or address.get("town") or address.get("village")
    county = address.get("county") or address.get("state")
    parts = [part for part in (neighbourhood, city or county) if part]
    if not parts:
        raise AppError(502, "geocoding_unavailable", "A pickup area could not be determined")
    return ", ".join(dict.fromkeys(parts))[:160]


def reverse_geocode(db: Session, latitude: float, longitude: float) -> str:
    latitude = round(latitude, 4)
    longitude = round(longitude, 4)
    cached = db.scalar(
        select(GeocodeCache).where(
            GeocodeCache.latitude == latitude,
            GeocodeCache.longitude == longitude,
        )
    )
    if cached is not None:
        return cached.area_name

    global _last_request_at
    with _request_lock:
        wait_seconds = 1.0 - (time.monotonic() - _last_request_at)
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        params = urlencode({"lat": latitude, "lon": longitude, "format": "jsonv2"})
        request = Request(
            f"https://nominatim.openstreetmap.org/reverse?{params}",
            headers={"User-Agent": settings.nominatim_user_agent},
        )
        try:
            with urlopen(request, timeout=10) as response:
                data = json.loads(response.read())
        except (URLError, TimeoutError, OSError, json.JSONDecodeError):
            _last_request_at = time.monotonic()
            raise AppError(
                502,
                "geocoding_unavailable",
                "Pickup area lookup is temporarily unavailable",
            ) from None
        _last_request_at = time.monotonic()

    area_name = _area_name(data.get("address") or {})
    db.add(
        GeocodeCache(
            latitude=latitude,
            longitude=longitude,
            area_name=area_name,
        )
    )
    db.commit()
    return area_name
