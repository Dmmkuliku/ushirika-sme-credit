import io
from datetime import datetime, timedelta

import pandas as pd
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models import PaymentStatus, SMEProfile, Transaction, User
from app.schemas.transaction import PaymentStatus as SchemaPaymentStatus
from app.utils.pseudonymization import pseudonymize

REQUIRED_COLUMNS = [
    "transaction_ref",
    "counterparty_tin",
    "counterparty_name",
    "counterparty_type",
    "order_type",
    "amount_tzs",
    "payment_status",
    "transaction_date",
]

OPTIONAL_COLUMNS = [
    "notes",
]


def _parse_datetime(val) -> datetime:
    if isinstance(val, datetime):
        return val
    parsed = pd.to_datetime(val, utc=True)
    if pd.isna(parsed):
        raise ValueError(f"Invalid datetime: {val}")
    return parsed.to_pydatetime()


def _clean_tin(val) -> str:
    cleaned = "".join(ch for ch in str(val).strip().upper() if ch.isalnum())
    if len(cleaned) < 9:
        raise ValueError("TIN must be at least 9 characters")
    return cleaned


async def import_transactions_csv(
    db: Session,
    user: User,
    file: UploadFile,
) -> dict:
    profile = db.query(SMEProfile).filter(SMEProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SME profile not found")

    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid CSV: {exc}") from exc

    # Accept legacy CSVs that still have due_date instead of counterparty_tin
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if "counterparty_tin" in missing and "counterparty_name" in df.columns:
        missing = [c for c in missing if c != "counterparty_tin"]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required columns: {missing}",
        )

    imported = 0
    skipped = 0
    errors: list[str] = []

    existing_refs = {
        t.transaction_ref
        for t in db.query(Transaction.transaction_ref)
        .filter(Transaction.sme_profile_id == profile.id)
        .all()
    }

    for idx, row in df.iterrows():
        try:
            ref = str(row["transaction_ref"]).strip()
            if ref in existing_refs:
                skipped += 1
                continue

            status_val = str(row["payment_status"]).strip().lower()
            if status_val not in {s.value for s in SchemaPaymentStatus}:
                raise ValueError(f"Invalid payment status: {status_val}")

            name = str(row["counterparty_name"]).strip()
            if "counterparty_tin" in df.columns and pd.notna(row.get("counterparty_tin")):
                tin = _clean_tin(row["counterparty_tin"])
            else:
                # Legacy fallback — derive a placeholder TIN from name hash digits
                tin = "".join(ch for ch in pseudonymize(name, "tin") if ch.isdigit())[:9].ljust(9, "0")

            tx_date = _parse_datetime(row["transaction_date"])
            due = _parse_datetime(row["due_date"]) if "due_date" in df.columns and pd.notna(row.get("due_date")) else tx_date + timedelta(days=14)

            tx = Transaction(
                sme_profile_id=profile.id,
                transaction_ref=ref,
                counterparty_hash=pseudonymize(tin, "counterparty"),
                counterparty_tin=tin,
                counterparty_name=name,
                counterparty_type=str(row["counterparty_type"]).strip(),
                order_type=str(row["order_type"]).strip(),
                amount_tzs=float(row["amount_tzs"]),
                currency="TZS",
                payment_status=PaymentStatus(status_val),
                due_date=due,
                paid_date=tx_date if status_val == "paid" else None,
                days_delayed=0,
                compliance_flag=True,
                default_flag=status_val == "defaulted",
                completion_rate=1.0 if status_val == "paid" else 0.8,
                notes=str(row["notes"]).strip() if "notes" in df.columns and pd.notna(row.get("notes")) else None,
                transaction_date=tx_date,
            )
            db.add(tx)
            existing_refs.add(ref)
            imported += 1
        except Exception as exc:
            errors.append(f"Row {idx + 2}: {exc}")

    if imported:
        db.commit()

    return {"imported": imported, "skipped": skipped, "errors": errors}
