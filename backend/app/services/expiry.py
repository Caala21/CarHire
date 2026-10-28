from datetime import date, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import AuditLog, Vehicle, VehicleApprovalStatus

EXPIRY_AUDIT_REASON = "Document expired"
EXPIRY_WARNING_DAYS = 14


def check_vehicle_expiry(db: Session, actor_id: int | None = None) -> list[int]:
    today = date.today()
    expired_vehicles = db.scalars(
        select(Vehicle)
        .where(
            Vehicle.approval_status == VehicleApprovalStatus.APPROVED,
            or_(
                Vehicle.insurance_expiry < today,
                Vehicle.inspection_expiry < today,
            ),
        )
        .with_for_update()
    ).all()

    vehicle_ids: list[int] = []
    for vehicle in expired_vehicles:
        vehicle.approval_status = VehicleApprovalStatus.SUSPENDED
        vehicle.rejection_reason = EXPIRY_AUDIT_REASON
        db.add(
            AuditLog(
                actor_id=actor_id,
                action="suspend",
                target_type="vehicle",
                target_id=vehicle.id,
                reason=EXPIRY_AUDIT_REASON,
            )
        )
        vehicle_ids.append(vehicle.id)

    if expired_vehicles:
        db.commit()
    return vehicle_ids


def list_expiring_vehicles(db: Session) -> list[Vehicle]:
    today = date.today()
    deadline = today + timedelta(days=EXPIRY_WARNING_DAYS)
    return db.scalars(
        select(Vehicle)
        .where(
            Vehicle.approval_status == VehicleApprovalStatus.APPROVED,
            or_(
                Vehicle.insurance_expiry.between(today, deadline),
                Vehicle.inspection_expiry.between(today, deadline),
            ),
        )
        .order_by(Vehicle.insurance_expiry, Vehicle.inspection_expiry, Vehicle.id)
    ).all()
