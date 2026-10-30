import secrets
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import (
    OwnerProfile,
    OwnerVerificationStatus,
    Role,
    User,
    Vehicle,
    VehicleApprovalStatus,
    VehicleStatus,
)
from app.services.auth import hash_password

DEMO_OWNER_EMAIL = "demo-owner@example.invalid"
DEMO_OWNER_NATIONAL_ID = "DEMO-ID-NOT-REAL"
DEMO_OWNER_KRA_PIN = "DEMO-KRA-NOREAL"
DEMO_PHONE = "000000000000"
DEMO_VEHICLES = (
    {
        "plate": "DEMO-001",
        "make": "Toyota",
        "model": "Corolla",
        "year": 2022,
        "location": "Nairobi",
        "seats": 5,
        "transmission": "automatic",
        "fuel_type": "petrol",
        "daily_rate": Decimal("4500.00"),
        "deposit_amount": Decimal("15000.00"),
        "photos": ["https://placehold.co/800x600?text=Toyota+Corolla"],
    },
    {
        "plate": "DEMO-002",
        "make": "Mazda",
        "model": "CX-5",
        "year": 2021,
        "location": "Nairobi",
        "seats": 5,
        "transmission": "automatic",
        "fuel_type": "petrol",
        "daily_rate": Decimal("8500.00"),
        "deposit_amount": Decimal("25000.00"),
        "photos": ["https://placehold.co/800x600?text=Mazda+CX-5"],
    },
    {
        "plate": "DEMO-003",
        "make": "Subaru",
        "model": "Forester",
        "year": 2020,
        "location": "Nakuru",
        "seats": 5,
        "transmission": "automatic",
        "fuel_type": "petrol",
        "daily_rate": Decimal("7500.00"),
        "deposit_amount": Decimal("22000.00"),
        "photos": ["https://placehold.co/800x600?text=Subaru+Forester"],
    },
    {
        "plate": "DEMO-004",
        "make": "Nissan",
        "model": "Note",
        "year": 2022,
        "location": "Nakuru",
        "seats": 5,
        "transmission": "automatic",
        "fuel_type": "hybrid",
        "daily_rate": Decimal("4000.00"),
        "deposit_amount": Decimal("14000.00"),
        "photos": ["https://placehold.co/800x600?text=Nissan+Note"],
    },
    {
        "plate": "DEMO-005",
        "make": "Toyota",
        "model": "Land Cruiser Prado",
        "year": 2019,
        "location": "Mombasa",
        "seats": 7,
        "transmission": "automatic",
        "fuel_type": "diesel",
        "daily_rate": Decimal("12500.00"),
        "deposit_amount": Decimal("35000.00"),
        "photos": ["https://placehold.co/800x600?text=Toyota+Prado"],
    },
    {
        "plate": "DEMO-006",
        "make": "Mazda",
        "model": "Demio",
        "year": 2021,
        "location": "Mombasa",
        "seats": 5,
        "transmission": "automatic",
        "fuel_type": "petrol",
        "daily_rate": Decimal("3800.00"),
        "deposit_amount": Decimal("13000.00"),
        "photos": ["https://placehold.co/800x600?text=Mazda+Demio"],
    },
)


def _get_or_create_owner(db: Session) -> tuple[User, OwnerProfile, int]:
    user = db.scalar(select(User).where(User.email == DEMO_OWNER_EMAIL))
    created = 0
    if user is None:
        user = User(
            full_name="Demo CarHire Owner",
            email=DEMO_OWNER_EMAIL,
            phone=DEMO_PHONE,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            role=Role.OWNER,
            is_active=False,
        )
        db.add(user)
        db.flush()
        created = 1
    elif (
        user.role is not Role.OWNER
        or user.full_name != "Demo CarHire Owner"
        or user.phone != DEMO_PHONE
        or user.is_active
    ):
        raise ValueError(f"{DEMO_OWNER_EMAIL} exists but is not the inactive demo owner.")

    profile = db.get(OwnerProfile, user.id)
    if profile is None:
        profile = OwnerProfile(
            user_id=user.id,
            national_id=DEMO_OWNER_NATIONAL_ID,
            kra_pin=DEMO_OWNER_KRA_PIN,
            payout_phone=DEMO_PHONE,
            verification_status=OwnerVerificationStatus.APPROVED,
            reviewed_at=datetime.now(timezone.utc),
        )
        db.add(profile)
        db.flush()
    elif (
        profile.national_id != DEMO_OWNER_NATIONAL_ID
        or profile.kra_pin != DEMO_OWNER_KRA_PIN
        or profile.payout_phone != DEMO_PHONE
        or profile.verification_status is not OwnerVerificationStatus.APPROVED
        or profile.id_doc_url is not None
        or profile.selfie_url is not None
    ):
        raise ValueError(f"{DEMO_OWNER_EMAIL} has a non-demo owner profile.")

    return user, profile, created


def _seed_vehicles(db: Session, owner: User) -> int:
    created = 0
    for data in DEMO_VEHICLES:
        vehicle = db.scalar(select(Vehicle).where(Vehicle.plate == data["plate"]))
        if vehicle is not None:
            expected_values = {
                **data,
                "owner_id": owner.id,
                "approval_status": VehicleApprovalStatus.APPROVED,
                "status": VehicleStatus.AVAILABLE,
                "insurance_url": "https://example.invalid/demo/placeholder-insurance",
            }
            if any(getattr(vehicle, field) != value for field, value in expected_values.items()):
                raise ValueError(
                    f"Vehicle plate {data['plate']} exists but does not match demo data."
                )
            if (
                vehicle.chassis_number is not None
                or vehicle.logbook_url is not None
                or vehicle.insurance_expiry is None
                or vehicle.inspection_expiry is None
                or vehicle.insurance_expiry < date.today()
                or vehicle.inspection_expiry < date.today()
            ):
                raise ValueError(
                    f"Vehicle plate {data['plate']} contains non-demo or expired documents."
                )
            continue

        db.add(
            Vehicle(
                **data,
                owner_id=owner.id,
                insurance_url="https://example.invalid/demo/placeholder-insurance",
                insurance_expiry=date.today() + timedelta(days=365),
                inspection_expiry=date.today() + timedelta(days=365),
                approval_status=VehicleApprovalStatus.APPROVED,
                status=VehicleStatus.AVAILABLE,
                chassis_number=None,
                logbook_url=None,
            )
        )
        created += 1
    return created


def seed_demo(db: Session) -> tuple[int, int]:
    owner, _, owners_created = _get_or_create_owner(db)
    vehicles_created = _seed_vehicles(db, owner)
    db.commit()
    return owners_created, vehicles_created


def main() -> None:
    with SessionLocal() as db:
        owners_created, vehicles_created = seed_demo(db)
    print(
        "Demo seed complete: "
        f"{owners_created} owner and {vehicles_created} vehicles created."
    )


if __name__ == "__main__":
    main()
