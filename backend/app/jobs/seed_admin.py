import argparse
import getpass
import re
import sys
from collections.abc import Sequence

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import Role, User
from app.services.auth import hash_password

PHONE_PATTERN = re.compile(r"254[17]\d{8}")
MIN_PASSWORD_LENGTH = 12


def seed_admin(
    db: Session,
    *,
    email: str,
    full_name: str | None = None,
    phone: str | None = None,
    password: str | None = None,
    promote_existing: bool = False,
) -> tuple[User, bool]:
    existing_user = db.scalar(select(User).where(User.email == email))
    if existing_user is not None:
        if not promote_existing:
            raise ValueError("User already exists; pass --promote-existing to grant admin access.")
        changed = existing_user.role is not Role.ADMIN
        existing_user.role = Role.ADMIN
        db.commit()
        db.refresh(existing_user)
        return existing_user, changed

    if promote_existing:
        raise ValueError("Cannot promote: no account exists with that email.")
    if not full_name or not phone or password is None:
        raise ValueError("Creating an admin requires a name, phone, and password.")
    if PHONE_PATTERN.fullmatch(phone) is None:
        raise ValueError("Phone must use Kenyan international format, for example 254712345678.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

    user = User(
        full_name=full_name,
        email=email,
        phone=phone,
        password_hash=hash_password(password),
        role=Role.ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, True


def _arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or promote a CarHire admin account.")
    parser.add_argument("email", help="Admin account email address")
    parser.add_argument("--name", help="Full name (required when creating a new account)")
    parser.add_argument("--phone", help="Kenyan phone in 254XXXXXXXXX format (required when creating)")
    parser.add_argument(
        "--promote-existing",
        action="store_true",
        help="Grant admin role to an existing account without changing its password",
    )
    args = parser.parse_args(argv)
    try:
        args.email = str(TypeAdapter(EmailStr).validate_python(args.email)).lower()
    except ValidationError:
        parser.error("email must be a valid email address")

    if args.promote_existing and (args.name or args.phone):
        parser.error("--name and --phone are only used when creating a new account")
    if not args.promote_existing and (not args.name or not args.phone):
        parser.error("--name and --phone are required when creating a new account")
    if args.phone and PHONE_PATTERN.fullmatch(args.phone) is None:
        parser.error("--phone must use Kenyan international format, for example 254712345678")
    return args


def main(argv: Sequence[str] | None = None) -> None:
    args = _arguments(argv)
    password = None
    with SessionLocal() as db:
        existing_user = db.scalar(select(User).where(User.email == args.email))
        if existing_user is not None and not args.promote_existing:
            print("User already exists. Re-run with --promote-existing to grant admin access.")
            raise SystemExit(1)
        if existing_user is None and args.promote_existing:
            print("No account exists with that email; cannot promote.")
            raise SystemExit(1)

        if existing_user is None:
            password = getpass.getpass("New admin password: ")
            confirmation = getpass.getpass("Confirm new admin password: ")
            if password != confirmation:
                print("Passwords do not match.")
                raise SystemExit(1)
            if len(password) < MIN_PASSWORD_LENGTH:
                print(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
                raise SystemExit(1)

        _, changed = seed_admin(
            db,
            email=args.email,
            full_name=args.name,
            phone=args.phone,
            password=password,
            promote_existing=args.promote_existing,
        )

    if args.promote_existing and changed:
        print(f"Admin access granted to {args.email}.")
    elif args.promote_existing:
        print(f"{args.email} already has admin access.")
    else:
        print(f"Admin account created for {args.email}.")


if __name__ == "__main__":
    main(sys.argv[1:])
