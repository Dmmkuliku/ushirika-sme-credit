"""Restore admin and backfill missing SME TIN values on existing DBs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, engine
from app.models import SMEProfile, User, UserRole
from app.schema_migrate import migrate_schema
from app.utils.security import hash_pin

ADMIN_LOGIN_ID = "20031001121160000228"
ADMIN_PIN = "1234"
ADMIN_NAME = "System Administrator"
SUBADMIN_INITIAL_IDS = [
    "20020703214030000121",
    "20021105231230000121",
    "20041126334010000118",
    "20040110141080000214",
]

DEMO_TINS = {
    "19900101123456789012": "100123456",
    "19850515987654321098": "100234567",
    "19951231456789012345": "100345678",
}


def restore_admin() -> None:
    Base.metadata.create_all(bind=engine)
    migrate_schema()
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
        else:
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

        updated = 0
        for profile in db.query(SMEProfile).all():
            if profile.tin:
                continue
            tin = DEMO_TINS.get(profile.nida) or f"9{str(profile.id).zfill(8)}"
            profile.tin = tin
            updated += 1
        if updated:
            db.commit()
            print(f"Backfilled TIN for {updated} SME profile(s)")

        # Ensure fixed initial sub-admin accounts exist and can sign in with PIN 1234.
        created_subadmins = 0
        reset_subadmins = 0
        for idx, login_id in enumerate(SUBADMIN_INITIAL_IDS, start=1):
            sub = db.query(User).filter(User.login_id == login_id).first()
            if sub:
                sub.role = UserRole.SUBADMIN
                sub.is_active = True
                sub.hashed_pin = hash_pin(ADMIN_PIN)
                if not sub.full_name:
                    sub.full_name = f"Sub Admin {idx}"
                if not sub.gender:
                    sub.gender = "Other"
                reset_subadmins += 1
            else:
                db.add(
                    User(
                        login_id=login_id,
                        hashed_pin=hash_pin(ADMIN_PIN),
                        role=UserRole.SUBADMIN,
                        full_name=f"Sub Admin {idx}",
                        gender="Other",
                        is_active=True,
                    )
                )
                created_subadmins += 1
        if created_subadmins or reset_subadmins:
            db.commit()
            print(
                f"Sub-admin accounts ready: created {created_subadmins}, reset/updated {reset_subadmins} "
                f"(PIN {ADMIN_PIN})"
            )
    finally:
        db.close()


if __name__ == "__main__":
    restore_admin()
