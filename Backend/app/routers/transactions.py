from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.database import get_db
from app.dependencies import RequireSME
from app.models import PaymentStatus, SMEProfile, Transaction
from app.schemas.transaction import (
    CSVImportResult,
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)
from app.services.csv_export import export_estatement_csv
from app.services.csv_import import REQUIRED_COLUMNS, OPTIONAL_COLUMNS, import_transactions_csv
from app.services.monthly_history import refresh_monthly_history
from app.services.scoring_pipeline import score_after_data_change, schedule_background_retrain
from app.utils.pseudonymization import pseudonymize

router = APIRouter(prefix="/transactions", tags=["Transactions"])


def _get_sme_profile(db: Session, user_id: int) -> SMEProfile:
    profile = db.query(SMEProfile).filter(SMEProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SME profile not found")
    return profile


def _after_write(db: Session, user, profile_id: int) -> dict:
    """Score with current lender-facing model; retrain in background (never blocks upload)."""
    refresh_monthly_history(db, profile_id)
    score_info = score_after_data_change(db, user)
    if score_info.get("score_ready"):
        schedule_background_retrain()
    return score_info


def _coerce_payment_status(value) -> PaymentStatus:
    if isinstance(value, PaymentStatus):
        return value
    if hasattr(value, "value"):
        return PaymentStatus(value.value)
    return PaymentStatus(str(value).lower())


@router.post("", response_model=TransactionResponse, status_code=201)
def create_transaction(
    payload: TransactionCreate,
    current_user: RequireSME,
    db: Session = Depends(get_db),
):
    profile = _get_sme_profile(db, current_user.id)

    existing = (
        db.query(Transaction)
        .filter(Transaction.sme_profile_id == profile.id, Transaction.transaction_ref == payload.transaction_ref)
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Transaction ref already exists")

    due = payload.due_date or (payload.transaction_date + timedelta(days=14))
    paid = payload.paid_date
    if payload.payment_status == PaymentStatus.PAID and paid is None:
        paid = payload.transaction_date

    # Ensure timezone-aware UTC when client sends naive dates
    tx_date = payload.transaction_date
    if tx_date.tzinfo is None:
        from datetime import timezone

        tx_date = tx_date.replace(tzinfo=timezone.utc)
        if due and due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        if paid and paid.tzinfo is None:
            paid = paid.replace(tzinfo=timezone.utc)

    tx = Transaction(
        sme_profile_id=profile.id,
        transaction_ref=payload.transaction_ref,
        counterparty_hash=pseudonymize(payload.counterparty_tin or payload.counterparty_name, "counterparty"),
        counterparty_tin=payload.counterparty_tin,
        counterparty_name=payload.counterparty_name,
        counterparty_type=payload.counterparty_type,
        order_type=payload.order_type,
        amount_tzs=payload.amount_tzs,
        currency=payload.currency,
        payment_status=_coerce_payment_status(payload.payment_status),
        due_date=due,
        paid_date=paid,
        days_delayed=payload.days_delayed,
        compliance_flag=payload.compliance_flag,
        default_flag=payload.default_flag,
        completion_rate=payload.completion_rate,
        notes=payload.notes,
        transaction_date=tx_date,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    _after_write(db, current_user, profile.id)
    return tx


@router.get("", response_model=list[TransactionResponse])
def list_transactions(current_user: RequireSME, db: Session = Depends(get_db)):
    profile = db.query(SMEProfile).filter(SMEProfile.user_id == current_user.id).first()
    if not profile:
        return []
    return (
        db.query(Transaction)
        .filter(Transaction.sme_profile_id == profile.id)
        .order_by(Transaction.transaction_date.desc())
        .all()
    )


@router.post("/import", response_model=CSVImportResult)
async def import_csv(
    current_user: RequireSME,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
    name = (file.filename or "").lower()
    if not name.endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a CSV (.csv)")

    result = await import_transactions_csv(db, current_user, file)
    profile = db.query(SMEProfile).filter(SMEProfile.user_id == current_user.id).first()

    score_payload: dict = {}
    training_payload: dict = {}
    if profile and result["imported"] > 0:
        score_payload = _after_write(db, current_user, profile.id)
        # GridSearchCV takes minutes — never block the upload HTTP response (Render/Vercel timeout).
        schedule_background_retrain()
        training_payload = {
            "model_training_scheduled": True,
            "model_training_summary": {
                "note": (
                    "Model retraining runs in the background after this upload. "
                    "Your score above uses the current Random Forest model."
                ),
            },
        }

    return CSVImportResult(
        imported=result["imported"],
        skipped=result["skipped"],
        errors=result["errors"],
        model_retrained=False,
        model_version=score_payload.get("model_version"),
        score_ready=bool(score_payload.get("score_ready")),
        score=score_payload.get("score"),
        risk_band=score_payload.get("risk_band"),
        eligible_financing_tzs=score_payload.get("eligible_financing_tzs"),
        probability_creditworthy=score_payload.get("probability_creditworthy"),
        primary_model=score_payload.get("primary_model"),
        ml_features_display=score_payload.get("ml_features_display"),
        transaction_count=score_payload.get("transaction_count"),
        transactions_needed=score_payload.get("transactions_needed"),
        message=score_payload.get("message")
        or (
            f"Imported {result['imported']} row(s)."
            if result["imported"]
            else "No new rows imported."
        ),
        model_training_ran=bool(training_payload.get("model_training_ran", False)),
        model_training_scheduled=bool(training_payload.get("model_training_scheduled", False)),
        model_training_version=training_payload.get("model_training_version"),
        model_training_summary=training_payload.get("model_training_summary"),
    )


@router.get("/template")
def download_template(current_user: RequireSME):
    header = ",".join(REQUIRED_COLUMNS + OPTIONAL_COLUMNS)
    sample_rows = [
        "TX-1001,100123456,Dar Fresh Foods,buyer,sale,250000,paid,2025-01-10,On-time settlement",
        "TX-1002,100234567,Kilimo Supplies,seller,purchase,180000,paid,2025-01-20,Inventory restock",
        "TX-1003,100345678,Mwanza Distributors,buyer,sale,320000,partial,2025-02-05,Partial payment",
        "TX-1004,100456789,Arusha Traders,buyer,sale,150000,pending,2025-02-10,Awaiting balance",
        "TX-1005,100567890,Coastal Logistics,seller,purchase,210000,paid,2025-03-01,Logistics services",
    ]
    content = header + "\n" + "\n".join(sample_rows) + "\n"
    # BytesIO avoids some browser/proxy issues with text StreamingResponse
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="transaction_template.csv"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/export/estatement")
def download_estatement(current_user: RequireSME, db: Session = Depends(get_db)):
    csv_content = export_estatement_csv(db, current_user)
    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8")),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="e-statement.csv"',
            "Cache-Control": "no-store",
        },
    )


@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    current_user: RequireSME,
    db: Session = Depends(get_db),
):
    profile = _get_sme_profile(db, current_user.id)
    tx = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.sme_profile_id == profile.id)
        .first()
    )
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    data = payload.model_dump(exclude_unset=True)
    if "counterparty_name" in data or "counterparty_tin" in data:
        tin = data.get("counterparty_tin", tx.counterparty_tin)
        name = data.get("counterparty_name", tx.counterparty_name)
        if tin or name:
            tx.counterparty_hash = pseudonymize(tin or name, "counterparty")
    if "transaction_ref" in data and data["transaction_ref"] is not None:
        new_ref = data["transaction_ref"]
        clash = (
            db.query(Transaction)
            .filter(
                Transaction.sme_profile_id == profile.id,
                Transaction.transaction_ref == new_ref,
                Transaction.id != tx.id,
            )
            .first()
        )
        if clash:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Transaction ref already exists")
    if "payment_status" in data and data["payment_status"] is not None:
        data["payment_status"] = _coerce_payment_status(data["payment_status"])

    for field, value in data.items():
        setattr(tx, field, value)

    db.commit()
    db.refresh(tx)
    _after_write(db, current_user, profile.id)
    return tx


@router.delete("/{transaction_id}", status_code=204, response_class=Response)
def delete_transaction(transaction_id: int, current_user: RequireSME, db: Session = Depends(get_db)):
    profile = _get_sme_profile(db, current_user.id)
    tx = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.sme_profile_id == profile.id)
        .first()
    )
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    db.delete(tx)
    db.commit()
    _after_write(db, current_user, profile.id)
    return Response(status_code=204)
