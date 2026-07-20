"""Seed demo data for SME Credit Risk backend."""

import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, engine
from app.models import LenderProfile, PaymentStatus, SMEProfile, Transaction, User, UserRole
from app.services.credit_scoring import score_sme
from app.services.monthly_history import refresh_monthly_history
from app.utils.pseudonymization import generate_display_token, pseudonymize
from app.utils.security import hash_pin

COUNTERPARTIES = [
    ("Kilimanjaro Traders Ltd", "distributor"),
    ("Dar Fresh Produce", "supplier"),
    ("Mwanza Logistics Co", "logistics"),
    ("Arusha Agro Supply", "supplier"),
    ("Coastal Retail Chain", "buyer"),
    ("Lake Zone Exporters", "buyer"),
    ("Tanga Port Services", "logistics"),
    ("Mbeya Grain Collective", "supplier"),
]

SME_SPECS = [
    (
        "19900101123456789012",
        "Grace Mwangi",
        "Entrepreneur",
        "+255712345001",
        "Dar es Salaam, Kinondoni",
        date(1990, 1, 1),
        "100123456",
    ),
    (
        "19850515987654321098",
        "John Kimaro",
        "Machinga",
        "+255712345002",
        "Arusha, Central Market",
        date(1985, 5, 15),
        "100234567",
    ),
    (
        "19951231456789012345",
        "Fatuma Saidi",
        "Retailer",
        "+255712345003",
        "Mwanza, Nyamagana",
        date(1995, 12, 31),
        "100345678",
    ),
]

SUBADMIN_IDS = [
    "20020703214030000121",
    "20021105231230000121",
    "20041126334010000118",
    "20040110141080000214",
]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        if db.query(User).filter(User.login_id == "20031001121160000228").first():
            for user in db.query(User).filter(User.role == UserRole.SME).all():
                try:
                    score_sme(db, user, force_refresh=True)
                except ValueError:
                    pass
            print("Demo data already seeded.")
            print("Existing SME scores refreshed.")
            return

        admin = User(
            login_id="20031001121160000228",
            hashed_pin=hash_pin("1234"),
            role=UserRole.ADMIN,
            full_name="System Administrator",
            gender="Male",
        )
        db.add(admin)
        db.flush()

        lender1_user = User(
            login_id="EMP001",
            hashed_pin=hash_pin("1234"),
            role=UserRole.LENDER,
            full_name="James Mwangi",
            gender="Male",
        )
        db.add(lender1_user)
        db.flush()
        db.add(
            LenderProfile(
                user_id=lender1_user.id,
                membership_number="EMP001",
                organization="CRDB",
                work_email="james.mwangi@crdb.co.tz",
                phone="+255712000001",
            )
        )

        lender2_user = User(
            login_id="EMP002",
            hashed_pin=hash_pin("1234"),
            role=UserRole.LENDER,
            full_name="Amina Hassan",
            gender="Female",
        )
        db.add(lender2_user)
        db.flush()
        db.add(
            LenderProfile(
                user_id=lender2_user.id,
                membership_number="EMP002",
                organization="NMB",
                work_email="amina.hassan@nmb.co.tz",
                phone="+255712000002",
            )
        )

        for idx, sub_id in enumerate(SUBADMIN_IDS, start=1):
            db.add(
                User(
                    login_id=sub_id,
                    hashed_pin=hash_pin("1234"),
                    role=UserRole.SUBADMIN,
                    full_name=f"Sub Admin {idx}",
                    gender="Other",
                )
            )

        rng = random.Random(42)
        now = datetime.now(timezone.utc)

        for nida, full_name, business_type, phone, location, dob, tin in SME_SPECS:
            user = User(
                login_id=nida,
                hashed_pin=hash_pin("1234"),
                role=UserRole.SME,
                full_name=full_name,
                gender="Female" if full_name.split()[0] in ("Grace", "Fatuma", "Amina") else "Male",
            )
            db.add(user)
            db.flush()

            profile = SMEProfile(
                user_id=user.id,
                nida=nida,
                phone=phone,
                email=f"{full_name.split()[0].lower()}@example.co.tz",
                location=location,
                nationality="Tanzanian",
                date_of_birth=dob,
                business_type=business_type,
                tin=tin,
                display_token=generate_display_token(),
            )
            db.add(profile)
            db.flush()

            for i in range(12):
                cp_name, cp_type = rng.choice(COUNTERPARTIES)
                tx_date = now - timedelta(days=rng.randint(10, 330) + i * 7)
                due_date = tx_date + timedelta(days=rng.randint(7, 30))
                paid_date = due_date - timedelta(days=rng.randint(0, 5))
                days_delayed = max(0, (paid_date - due_date).days)
                # Typical SME deals stay under ~1M; rare large deals become outliers
                amount = rng.randint(80_000, 900_000) if i < 11 else rng.randint(4_000_000, 8_000_000)
                cp_tin = f"200{rng.randint(100000, 999999)}"

                db.add(
                    Transaction(
                        sme_profile_id=profile.id,
                        transaction_ref=f"TX-{nida[-4:]}-{i + 1:03d}",
                        counterparty_hash=pseudonymize(cp_tin, "counterparty"),
                        counterparty_tin=cp_tin,
                        counterparty_name=cp_name,
                        counterparty_type=cp_type,
                        order_type=rng.choice(["sale", "purchase", "service"]),
                        amount_tzs=float(amount),
                        payment_status=PaymentStatus.PAID,
                        due_date=due_date,
                        paid_date=paid_date,
                        days_delayed=days_delayed,
                        compliance_flag=True,
                        default_flag=False,
                        completion_rate=1.0,
                        transaction_date=tx_date,
                    )
                )

            refresh_monthly_history(db, profile.id)
            score_sme(db, user, force_refresh=True)

        db.commit()
        print("Demo data seeded successfully.")
        print("Admin ID: 20031001121160000228  PIN: 1234")
        print("Lenders: EMP001 / EMP002  PIN: 1234")
        print("SMEs: use NIDA numbers above  PIN: 1234")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
