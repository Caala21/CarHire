import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.core.database import Base


def test_users_role_check_constraint_rejects_unknown_role():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with engine.begin() as connection:
        with pytest.raises(IntegrityError):
            connection.execute(
                text(
                    "INSERT INTO users (full_name, email, password_hash, role, is_active) "
                    "VALUES ('Test User', 'test@example.com', 'hash', 'manager', 1)"
                )
            )

    Base.metadata.drop_all(engine)
    engine.dispose()
