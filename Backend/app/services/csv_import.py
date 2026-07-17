import io
from datetime import datetime

import pandas as pd
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models import PaymentStatus, SMEProfile, Transaction, User
from app.schemas.transaction import PaymentStatus as SchemaPaymentStatus
from app.utils.pseudonymization import pseudonymize

REQUIRED_COLUMNS = [
    "transaction_ref",
    "counterparty_name",
    "counterparty_type",
    "order_type",
    "amount_tzs",
    "payment_status",
    "due_date",
    "transaction_date",
]

OPTIONAL_COLUMNS = [
    "currency",
    "paid_date",
    "days_delayed",
    "compliance_flag",
    "default_flag",
    "completion_rate",
    "notes",
]


def _parse_bool(val) -> bool:
    if isinstance(val, bool):
        return val
    if pd.isna(val):
        return True
    return str(val).strip().lower() in ("true", "1", "yes", "y")


def _parse_datetime(val) -> datetime:
    if isinstance(val, datetime):
        return val
    parsed = pd.to_datetime(val, utc=True)
    if pd.isna(parsed):
        raise ValueError(f"Invalid datetime: {val}")
    return parsed.to_pydatetime()


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

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
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
                raise ValueError(f"Invalid payment_status: {status_val}")

            tx = Transaction(
                sme_profile_id=profile.id,
                transaction_ref=ref,
                counterparty_hash=pseudonymize(str(row["counterparty_name"]), "counterparty"),
                counterparty_type=str(row["counterparty_type"]).strip(),
                order_type=str(row["order_type"]).strip(),
                amount_tzs=float(row["amount_tzs"]),
                currency=str(row.get("currency", "TZS")).strip() if pd.notna(row.get("currency")) else "TZS",
                payment_status=PaymentStatus(status_val),
                due_date=_parse_datetime(row["due_date"]),
                paid_date=_parse_datetime(row["paid_date"]) if pd.notna(row.get("paid_date")) else None,
                days_delayed=int(row.get("days_delayed", 0)) if pd.notna(row.get("days_delayed")) else 0,
                compliance_flag=_parse_bool(row.get("compliance_flag", True)),
                default_flag=_parse_bool(row.get("default_flag", False)),
                completion_rate=float(row.get("completion_rate", 1.0)) if pd.notna(row.get("completion_rate")) else 1.0,
                notes=(
                    pseudonymize(str(row["notes"]), "transaction_notes")
                    if pd.notna(row.get("notes"))
                    else None
                ),
                transaction_date=_parse_datetime(row["transaction_date"]),
            )
            db.add(tx)
            existing_refs.add(ref)
            imported += 1
        except Exception as exc:
            errors.append(f"Row {idx + 2}: {exc}")

    if imported:
        db.commit()

    return {"imported": imported, "skipped": skipped, "errors": errors}
