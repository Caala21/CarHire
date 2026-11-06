from app.core.database import SessionLocal
from app.services.mpesa import list_reconciliation_candidates, reconcile_payment


def main() -> None:
    with SessionLocal() as db:
        payments = list_reconciliation_candidates(db)
        reconciled = sum(reconcile_payment(db, payment) for payment in payments)
    print(f"Checked {len(payments)} pending M-Pesa payment(s); reconciled {reconciled}.")


if __name__ == "__main__":
    main()
