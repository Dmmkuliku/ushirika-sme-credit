import io

import pandas as pd
from sqlalchemy.orm import Session

from app.models import SMEProfile, Transaction, User


def export_estatement_for_profile(db: Session, sme_profile_id: int) -> str:
    transactions = (
        db.query(Transaction)
        .filter(Transaction.sme_profile_id == sme_profile_id)
        .order_by(Transaction.transaction_date.desc())
        .all()
    )

    rows = [
        {
            "transaction_ref": t.transaction_ref,
            "counterparty_hash": t.counterparty_hash,
            "counterparty_type": t.counterparty_type,
            "order_type": t.order_type,
            "amount_tzs": t.amount_tzs,
            "currency": t.currency,
            "payment_status": t.payment_status.value,
            "due_date": t.due_date.isoformat(),
            "paid_date": t.paid_date.isoformat() if t.paid_date else "",
            "days_delayed": t.days_delayed,
            "compliance_flag": t.compliance_flag,
            "default_flag": t.default_flag,
            "completion_rate": t.completion_rate,
            "transaction_date": t.transaction_date.isoformat(),
            "notes": t.notes or "",
        }
        for t in transactions
    ]

    df = pd.DataFrame(rows)
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue()


def export_estatement_csv(db: Session, user: User) -> str:
    profile = db.query(SMEProfile).filter(SMEProfile.user_id == user.id).first()
    if not profile:
        return ""
    return export_estatement_for_profile(db, profile.id)
