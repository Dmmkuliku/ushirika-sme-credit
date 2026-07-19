import io

import pandas as pd
from sqlalchemy.orm import Session

from app.models import SMEProfile, Transaction, User


def export_estatement_for_profile(db: Session, sme_profile_id: int) -> str:
    """Export in template-compatible columns so SMEs can re-upload if needed."""
    transactions = (
        db.query(Transaction)
        .filter(Transaction.sme_profile_id == sme_profile_id)
        .order_by(Transaction.transaction_date.desc())
        .all()
    )

    rows = [
        {
            "transaction_ref": t.transaction_ref,
            "counterparty_tin": t.counterparty_tin or "",
            "counterparty_name": t.counterparty_name or "",
            "counterparty_type": t.counterparty_type,
            "order_type": t.order_type,
            "amount_tzs": t.amount_tzs,
            "payment_status": t.payment_status.value,
            "transaction_date": t.transaction_date.date().isoformat()
            if hasattr(t.transaction_date, "date")
            else str(t.transaction_date)[:10],
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
