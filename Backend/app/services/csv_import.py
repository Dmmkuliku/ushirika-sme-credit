import io
from datetime import datetime, timedelta, timezone

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

CSV_HEADERS = {
    "en": {
        "transaction_ref": "Receipt No.",
        "counterparty_tin": "Customer or supplier TIN",
        "counterparty_name": "Customer or supplier name",
        "counterparty_type": "Was this a customer or supplier?",
        "order_type": "What was the payment for?",
        "amount_tzs": "Amount paid (TZS)",
        "payment_status": "Was the payment completed?",
        "transaction_date": "Payment date",
        "notes": "Extra details",
    },
    "sw": {
        "transaction_ref": "Namba ya Stakabadhi",
        "counterparty_tin": "TIN ya mteja au msambazaji",
        "counterparty_name": "Jina la mteja au msambazaji",
        "counterparty_type": "Alikuwa mteja au msambazaji?",
        "order_type": "Malipo yalikuwa ya nini?",
        "amount_tzs": "Kiasi kilicholipwa (TZS)",
        "payment_status": "Malipo yamekamilika?",
        "transaction_date": "Tarehe ya malipo",
        "notes": "Maelezo ya ziada",
    },
}


def _normalize_header(value: str) -> str:
    return " ".join(str(value).strip().lower().split())


HEADER_ALIASES = {
    _normalize_header(label): canonical
    for headers in CSV_HEADERS.values()
    for canonical, label in headers.items()
}
HEADER_ALIASES.update({column: column for column in REQUIRED_COLUMNS + OPTIONAL_COLUMNS})

PARTY_ALIASES = {
    "buyer": "buyer",
    "customer": "buyer",
    "mteja": "buyer",
    "seller": "seller",
    "supplier": "seller",
    "vendor": "seller",
    "distributor": "distributor",
    "msambazaji": "seller",
}
ORDER_ALIASES = {
    "sale": "sale",
    "uuzaji": "sale",
    "purchase": "purchase",
    "ununuzi": "purchase",
    "service": "service",
    "huduma": "service",
}
PAYMENT_STATUS_ALIASES = {
    "pending": "pending",
    "inasubiri": "pending",
    "paid": "paid",
    "imelipwa": "paid",
    "partial": "partial",
    "sehemu": "partial",
    "overdue": "overdue",
    "imechelewa": "overdue",
    "defaulted": "defaulted",
    "haijalipwa": "defaulted",
}


def _parse_datetime(val) -> datetime:
    if isinstance(val, datetime):
        return val
    parsed = pd.to_datetime(val, utc=True)
    if pd.isna(parsed):
        raise ValueError(f"Invalid datetime: {val}")
    return parsed.to_pydatetime()


def _clean_tin(val) -> str:
    """Normalize TIN to exactly 9 digits; avoid float corruption."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        raise ValueError("TIN is required")
    if hasattr(val, "item"):
        try:
            val = val.item()
        except Exception:
            pass
    if isinstance(val, float):
        if val == int(val):
            val = int(val)
        else:
            val = format(val, "f").rstrip("0").rstrip(".")
    elif isinstance(val, int):
        val = str(val)
    digits = "".join(ch for ch in str(val).strip() if ch.isdigit())
    if len(digits) != 9:
        raise ValueError("TIN must be exactly 9 digits")
    return digits


def _normalize_party(val: str) -> str:
    v = str(val).strip().lower()
    normalized = PARTY_ALIASES.get(v)
    if normalized is None:
        raise ValueError(f"Invalid customer or supplier value: {val}.")
    return normalized


def _normalize_order(val: str) -> str:
    v = str(val).strip().lower()
    normalized = ORDER_ALIASES.get(v)
    if normalized is None:
        raise ValueError(f"Invalid payment purpose: {val}.")
    return normalized


async def import_transactions_csv(
    db: Session,
    user: User,
    file: UploadFile,
) -> dict:
    profile = db.query(SMEProfile).filter(SMEProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SME profile not found")

    content = await file.read()
    if not content or not content.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV file is empty")

    try:
        df = pd.read_csv(
            io.BytesIO(content),
            dtype=str,
            keep_default_na=False,
            na_values=["", "NA", "N/A", "null", "None"],
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid CSV: {exc}") from exc

    # Normalize headers
    df.columns = [
        HEADER_ALIASES.get(_normalize_header(c), _normalize_header(c))
        for c in df.columns
    ]

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
            if not ref or ref.lower() == "nan":
                raise ValueError("transaction_ref is empty")
            if ref in existing_refs:
                skipped += 1
                continue

            status_raw = str(row["payment_status"]).strip().lower()
            status_val = PAYMENT_STATUS_ALIASES.get(status_raw, status_raw)
            if status_val not in {s.value for s in SchemaPaymentStatus}:
                raise ValueError(f"Invalid payment status: {status_val}")

            name = str(row["counterparty_name"]).strip()
            if not name or name.lower() == "nan":
                raise ValueError("counterparty_name is empty")

            if "counterparty_tin" in df.columns and str(row.get("counterparty_tin", "")).strip() not in ("", "nan"):
                tin = _clean_tin(row["counterparty_tin"])
            else:
                tin = "".join(ch for ch in pseudonymize(name, "tin") if ch.isdigit())[:9].ljust(9, "0")

            tx_date = _parse_datetime(row["transaction_date"])
            if tx_date > datetime.now(timezone.utc):
                raise ValueError("transaction_date cannot be in the future")
            due = (
                _parse_datetime(row["due_date"])
                if "due_date" in df.columns and str(row.get("due_date", "")).strip() not in ("", "nan")
                else tx_date + timedelta(days=14)
            )

            party = _normalize_party(row["counterparty_type"])
            order = _normalize_order(row["order_type"])
            amount = float(str(row["amount_tzs"]).replace(",", "").strip())
            if amount <= 0:
                raise ValueError("amount_tzs must be greater than 0")

            notes_raw = row["notes"] if "notes" in df.columns else ""
            notes = str(notes_raw).strip() if str(notes_raw).strip() not in ("", "nan") else None

            tx = Transaction(
                sme_profile_id=profile.id,
                transaction_ref=ref,
                counterparty_hash=pseudonymize(tin, "counterparty"),
                counterparty_tin=tin,
                counterparty_name=name,
                counterparty_type=party,
                order_type=order,
                amount_tzs=amount,
                currency="TZS",
                payment_status=PaymentStatus(status_val),
                due_date=due,
                paid_date=tx_date if status_val == "paid" else None,
                days_delayed=0,
                compliance_flag=True,
                default_flag=status_val == "defaulted",
                completion_rate=1.0 if status_val == "paid" else 0.8,
                notes=notes,
                transaction_date=tx_date,
            )
            db.add(tx)
            existing_refs.add(ref)
            imported += 1
        except Exception as exc:
            errors.append(f"Row {int(idx) + 2}: {exc}")

    if imported:
        db.commit()

    return {"imported": imported, "skipped": skipped, "errors": errors}
