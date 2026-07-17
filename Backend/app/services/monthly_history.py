from sqlalchemy.orm import Session

from app.models import MonthlyHistory, SMEProfile, Transaction


def refresh_monthly_history(db: Session, sme_profile_id: int) -> list[MonthlyHistory]:
    transactions = (
        db.query(Transaction)
        .filter(Transaction.sme_profile_id == sme_profile_id)
        .order_by(Transaction.transaction_date.asc())
        .all()
    )

    db.query(MonthlyHistory).filter(MonthlyHistory.sme_profile_id == sme_profile_id).delete()

    if not transactions:
        db.commit()
        return []

    buckets: dict[str, dict] = {}
    for t in transactions:
        ym = t.transaction_date.strftime("%Y-%m")
        if ym not in buckets:
            buckets[ym] = {
                "total_volume_tzs": 0.0,
                "transaction_count": 0,
                "delay_sum": 0,
                "on_time": 0,
                "default_count": 0,
                "compliance_sum": 0,
            }
        b = buckets[ym]
        b["total_volume_tzs"] += t.amount_tzs
        b["transaction_count"] += 1
        b["delay_sum"] += t.days_delayed
        if t.days_delayed <= 3 and t.payment_status.value in ("paid", "partial"):
            b["on_time"] += 1
        if t.default_flag:
            b["default_count"] += 1
        if t.compliance_flag:
            b["compliance_sum"] += 1

    records = []
    for ym, b in sorted(buckets.items()):
        count = b["transaction_count"]
        record = MonthlyHistory(
            sme_profile_id=sme_profile_id,
            year_month=ym,
            total_volume_tzs=round(b["total_volume_tzs"], 2),
            transaction_count=count,
            avg_delay_days=round(b["delay_sum"] / count, 2),
            on_time_rate=round(b["on_time"] / count, 4),
            default_count=b["default_count"],
            compliance_rate=round(b["compliance_sum"] / count, 4),
        )
        db.add(record)
        records.append(record)

    db.commit()
    return records


def get_monthly_history(db: Session, user_id: int) -> list[MonthlyHistory]:
    profile = db.query(SMEProfile).filter(SMEProfile.user_id == user_id).first()
    if not profile:
        return []
    return (
        db.query(MonthlyHistory)
        .filter(MonthlyHistory.sme_profile_id == profile.id)
        .order_by(MonthlyHistory.year_month.desc())
        .all()
    )
