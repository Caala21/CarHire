from fastapi import APIRouter, Depends

from app.models import User
from app.routers.auth import require_role

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ping")
def admin_ping(user: User = Depends(require_role("admin"))) -> dict[str, str]:
    return {"message": "Admin access granted"}