"""Restore the default system administrator account if missing or inactive."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, engine
from app.models import User, UserRole
from app.utils.security import hash_pin

ADMIN_LOGIN_ID = "20031001121160000228"
ADMIN_PIN = "1234"
ADMIN_NAME = "System Administrator"


def restore_admin() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.login_id == ADMIN_LOGIN_ID).first()
        if admin:
            admin.is_active = True
            admin.hashed_pin = hash_pin(ADMIN_PIN)
            admin.full_name = ADMIN_NAME
            admin.gender = "Male"
            admin.role = UserRole.ADMIN
            db.commit()
            print(f"Administrator restored: ID {ADMIN_LOGIN_ID}, PIN {ADMIN_PIN}")
            return

        admin = User(
            login_id=ADMIN_LOGIN_ID,
            hashed_pin=hash_pin(ADMIN_PIN),
            role=UserRole.ADMIN,
            full_name=ADMIN_NAME,
            gender="Male",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"Administrator created: ID {ADMIN_LOGIN_ID}, PIN {ADMIN_PIN}")
    finally:
        db.close()


if __name__ == "__main__":
    restore_admin()
