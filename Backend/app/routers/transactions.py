from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.config import get_settings
from app.database import get_db
from app.dependencies import RequireSME
from app.models import PaymentStatus, SMEProfile, Transaction
from app.schemas.transaction import (
    CSVImportResult,
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)
from app.services.credit_scoring import score_sme
from app.services.csv_export import export_estatement_csv
from app.services.csv_import import REQUIRED_COLUMNS, OPTIONAL_COLUMNS, import_transactions_csv
from app.services.monthly_history import refresh_monthly_history
from app.utils.pseudonymization import pseudonymize

router = APIRouter(prefix="/transactions", tags=["Transactions"])


def _get_sme_profile(db: Session, user_id: int) -> SMEProfile:
    profile = db.query(SMEProfile).filter(SMEProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SME profile not found")
    return profile


def _maybe_rescore(db: Session, user, profile_id: int) -> None:
    tx_count = db.query(Transaction).filter(Transaction.sme_profile_id == profile_id).count()
    if tx_count >= get_settings().min_transactions_for_score:
        try:
            score_sme(db, user, force_refresh=True)
        except Exception:
            pass


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

    tx = Transaction(
        sme_profile_id=profile.id,
        transaction_ref=payload.transaction_ref,
        counterparty_hash=pseudonymize(payload.counterparty_name, "counterparty"),
        counterparty_type=payload.counterparty_type,
        order_type=payload.order_type,
        amount_tzs=payload.amount_tzs,
        currency=payload.currency,
        payment_status=_coerce_payment_status(payload.payment_status),
        due_date=payload.due_date,
        paid_date=payload.paid_date,
        days_delayed=payload.days_delayed,
        compliance_flag=payload.compliance_flag,
        default_flag=payload.default_flag,
        completion_rate=payload.completion_rate,
        notes=payload.notes,
        transaction_date=payload.transaction_date,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    refresh_monthly_history(db, profile.id)
    _maybe_rescore(db, current_user, profile.id)
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
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a CSV")
    result = await import_transactions_csv(db, current_user, file)
    profile = db.query(SMEProfile).filter(SMEProfile.user_id == current_user.id).first()
    if profile and result["imported"] > 0:
        refresh_monthly_history(db, profile.id)
        _maybe_rescore(db, current_user, profile.id)
    return result


@router.get("/template")
def download_template(current_user: RequireSME):
    header = ",".join(REQUIRED_COLUMNS + OPTIONAL_COLUMNS)
    sample_rows = [
        "TX-1001,Dar Fresh Foods,buyer,sale,2500000,paid,2025-01-15,2025-01-10,TZS,2025-01-14,0,true,false,1.0,On-time settlement",
        "TX-1002,Kilimo Supplies,supplier,purchase,1800000,paid,2025-02-01,2025-01-20,TZS,2025-01-30,0,true,false,1.0,Inventory restock",
        "TX-1003,Mwanza Distributors,distributor,sale,3200000,partial,2025-02-20,2025-02-05,TZS,2025-02-25,5,true,false,0.8,Partial payment received",
        "TX-1004,Arusha Traders,buyer,sale,1500000,overdue,2025-03-01,2025-02-10,TZS,,12,false,false,0.6,Awaiting balance",
        "TX-1005,Coastal Logistics,supplier,purchase,2100000,paid,2025-03-15,2025-03-01,TZS,2025-03-12,0,true,false,1.0,Logistics services",
    ]
    content = header + "\n" + "\n".join(sample_rows) + "\n"
    return StreamingResponse(
        io.StringIO(content),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="transaction_template.csv"'},
    )


@router.get("/export/estatement")
def download_estatement(current_user: RequireSME, db: Session = Depends(get_db)):
    csv_content = export_estatement_csv(db, current_user)
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="e-statement.csv"'},
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
    if "counterparty_name" in data:
        name = data.pop("counterparty_name")
        if name:
            tx.counterparty_hash = pseudonymize(name, "counterparty")
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
    refresh_monthly_history(db, profile.id)
    _maybe_rescore(db, current_user, profile.id)
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
    refresh_monthly_history(db, profile.id)
    _maybe_rescore(db, current_user, profile.id)
    return Response(status_code=204)