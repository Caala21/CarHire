from app.core.database import SessionLocal
from app.services.bookings import expire_pending_bookings
from app.services.expiry import check_vehicle_expiry


def main() -> None:
    with SessionLocal() as db:
        suspended_ids = check_vehicle_expiry(db)
        expired_bookings = expire_pending_bookings(db)
    print(
        f"Suspended {len(suspended_ids)} expired vehicle(s); "
        f"expired {expired_bookings} unpaid booking hold(s)."
    )


if __name__ == "__main__":
    main()
