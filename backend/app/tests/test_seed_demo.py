from sqlalchemy import select

from app.core.database import get_db
from app.models import OwnerProfile, OwnerVerificationStatus, User, Vehicle, VehicleApprovalStatus
from app.seed_demo import DEMO_OWNER_EMAIL, seed_demo


def test_seed_demo_is_idempotent_and_uses_placeholders(client):
    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        assert seed_demo(db) == (1, 6)
        assert seed_demo(db) == (0, 0)

        owner = db.scalar(select(User).where(User.email == DEMO_OWNER_EMAIL))
        profile = db.get(OwnerProfile, owner.id)
        vehicles = db.scalars(select(Vehicle).order_by(Vehicle.plate)).all()

        assert owner.is_active is False
        assert profile.verification_status is OwnerVerificationStatus.APPROVED
        assert profile.id_doc_url is None
        assert profile.selfie_url is None
        assert len(vehicles) == 6
        assert {vehicle.location for vehicle in vehicles} == {
            "Nairobi",
            "Nakuru",
            "Mombasa",
        }
        assert {vehicle.make for vehicle in vehicles} == {
            "Toyota",
            "Mazda",
            "Subaru",
            "Nissan",
        }
        assert all(
            vehicle.owner_id == owner.id
            and vehicle.approval_status is VehicleApprovalStatus.APPROVED
            and vehicle.chassis_number is None
            and vehicle.logbook_url is None
            and vehicle.photos[0].startswith("https://placehold.co/")
            for vehicle in vehicles
        )
    finally:
        generator.close()
