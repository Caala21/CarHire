from app.core.database import SessionLocal
from app.services.expiry import check_vehicle_expiry


def main() -> None:
    with SessionLocal() as db:
        suspended_ids = check_vehicle_expiry(db)
    print(f"Suspended {len(suspended_ids)} expired vehicle(s).")


if __name__ == "__main__":
    main()
