from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import CreditScore, SMEProfile, Transaction, User, UserRole
from app.schemas.dashboard import DashboardSummary, SMEDashboardSummary, SMEDetailResponse, SMEPortfolioItem
from app.schemas.dashboard import MonthlyHistoryResponse


def lender_dashboard(db: Session) -> DashboardSummary:
    total_smes = db.query(SMEProfile).count()
    total_transactions = db.query(Transaction).count()
    total_volume = db.query(func.coalesce(func.sum(Transaction.amount_tzs), 0.0)).scalar() or 0.0

    latest_scores_subq = (
        db.query(CreditScore.user_id, func.max(CreditScore.id).label("max_id"))
        .group_by(CreditScore.user_id)
        .subquery()
    )
    latest_scores = (
        db.query(CreditScore)
        .join(latest_scores_subq, CreditScore.id == latest_scores_subq.c.max_id)
        .all()
    )

    scores = [s.score for s in latest_scores]
    avg_score = round(sum(scores) / len(scores), 2) if scores else None

    high = sum(1 for s in latest_scores if s.risk_band == "high")
    medium = sum(1 for s in latest_scores if s.risk_band == "medium")
    low = sum(1 for s in latest_scores if s.risk_band == "low")
    financing_total = sum(s.eligible_financing_tzs for s in latest_scores)

    return DashboardSummary(
        total_smes=total_smes,
        total_transactions=total_transactions,
        total_volume_tzs=round(float(total_volume), 2),
        average_score=avg_score,
        high_risk_count=high,
        medium_risk_count=medium,
        low_risk_count=low,
        eligible_financing_total_tzs=round(financing_total, 2),
    )


def sme_dashboard(db: Session, user: User) -> SMEDashboardSummary:
    import json

    from app.services.labels import humanize_features

    settings = get_settings()
    profile = db.query(SMEProfile).filter(SMEProfile.user_id == user.id).first()
    if not profile:
        return SMEDashboardSummary(
            transaction_count=0,
            total_volume_tzs=0.0,
            latest_score=None,
            risk_band=None,
            eligible_financing_tzs=None,
            score_eligible=False,
            score_locked=True,
            transactions_needed=settings.min_transactions_for_score,
            score_components=None,
            score_components_display=None,
        )

    tx_count = db.query(Transaction).filter(Transaction.sme_profile_id == profile.id).count()
    total_volume = (
        db.query(func.coalesce(func.sum(Transaction.amount_tzs), 0.0))
        .filter(Transaction.sme_profile_id == profile.id)
        .scalar()
        or 0.0
    )
    latest = (
        db.query(CreditScore)
        .filter(CreditScore.user_id == user.id)
        .order_by(CreditScore.created_at.desc())
        .first()
    )
    score_eligible = tx_count >= settings.min_transactions_for_score
    components = None
    display = None
    outlier_count = None
    typical_vol = None
    if latest and latest.features_json:
        try:
            components = json.loads(latest.features_json)
            display = humanize_features(components)
            outlier_count = int(components.get("outlier_transaction_count") or 0)
            typical_vol = components.get("typical_volume_tzs")
        except json.JSONDecodeError:
            components = None

    return SMEDashboardSummary(
        transaction_count=tx_count,
        total_volume_tzs=round(float(total_volume), 2),
        latest_score=latest.score if latest else None,
        risk_band=latest.risk_band if latest else None,
        eligible_financing_tzs=latest.eligible_financing_tzs if latest else None,
        score_eligible=score_eligible,
        score_locked=not score_eligible or latest is None,
        transactions_needed=max(0, settings.min_transactions_for_score - tx_count),
        score_components=components,
        score_components_display=display,
        outlier_transaction_count=outlier_count,
        typical_volume_tzs=typical_vol,
        model_version=latest.model_version if latest else None,
    )


def lender_portfolio(
    db: Session,
    q: str | None = None,
    risk: str | None = None,
    min_score: float | None = None,
    max_score: float | None = None,
) -> list[SMEPortfolioItem]:
    profiles = db.query(SMEProfile).all()
    items = []
    query = (q or "").strip().lower()
    risk_filter = (risk or "").strip().lower() or None

    for p in profiles:
        user = db.query(User).filter(User.id == p.user_id).first()
        tx_count = db.query(Transaction).filter(Transaction.sme_profile_id == p.id).count()
        latest = (
            db.query(CreditScore)
            .join(User, CreditScore.user_id == User.id)
            .filter(User.id == p.user_id)
            .order_by(CreditScore.created_at.desc())
            .first()
        )
        last_tx = (
            db.query(Transaction.transaction_date)
            .filter(Transaction.sme_profile_id == p.id)
            .order_by(Transaction.transaction_date.desc())
            .first()
        )
        full_name = user.full_name if user else ""
        item = SMEPortfolioItem(
            sme_profile_id=p.id,
            display_token=p.display_token,
            business_type=p.business_type,
            nida=p.nida,
            full_name=full_name,
            transaction_count=tx_count,
            latest_score=latest.score if latest else None,
            risk_band=latest.risk_band if latest else None,
            eligible_financing_tzs=latest.eligible_financing_tzs if latest else None,
            last_activity=last_tx[0] if last_tx else None,
        )

        if query:
            haystack = f"{item.display_token} {item.business_type} {item.nida} {item.full_name} {item.sme_profile_id}".lower()
            if query not in haystack:
                continue
        if risk_filter and (item.risk_band or "").lower() != risk_filter:
            continue
        if min_score is not None and (item.latest_score is None or item.latest_score < min_score):
            continue
        if max_score is not None and (item.latest_score is None or item.latest_score > max_score):
            continue
        items.append(item)
    return items


def lender_sme_detail(db: Session, sme_profile_id: int) -> SMEDetailResponse | None:
    import json

    from app.services.feature_engineering import FEATURE_COLUMNS, compute_features
    from app.services.labels import humanize_features
    from app.services.ml_predictor import get_predictor

    profile = db.query(SMEProfile).filter(SMEProfile.id == sme_profile_id).first()
    if not profile:
        return None

    settings = get_settings()
    user = db.query(User).filter(User.id == profile.user_id).first()
    transactions = (
        db.query(Transaction)
        .filter(Transaction.sme_profile_id == profile.id)
        .order_by(Transaction.transaction_date.asc())
        .all()
    )
    total_volume = sum(t.amount_tzs for t in transactions)
    latest = (
        db.query(CreditScore)
        .filter(CreditScore.user_id == profile.user_id)
        .order_by(CreditScore.created_at.desc())
        .first()
    )

    from app.models import MonthlyHistory

    history = (
        db.query(MonthlyHistory)
        .filter(MonthlyHistory.sme_profile_id == profile.id)
        .order_by(MonthlyHistory.year_month.desc())
        .all()
    )

    tx_count = len(transactions)
    score_eligible = tx_count >= settings.min_transactions_for_score
    ml_features = None
    ml_display = None
    probability = None
    model_version = latest.model_version if latest else None
    primary_model = None
    outlier_count = None
    typical_vol = None
    score = latest.score if latest else None
    risk = latest.risk_band if latest else None
    eligible = latest.eligible_financing_tzs if latest else None

    if score_eligible and transactions:
        feats = compute_features(transactions, profile.date_of_birth.year)
        if latest and latest.features_json:
            try:
                stored = json.loads(latest.features_json)
                feats = {**feats, **{k: float(v) for k, v in stored.items() if isinstance(v, (int, float))}}
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        ml_features = {k: float(feats.get(k, 0.0)) for k in FEATURE_COLUMNS}
        # Keep display extras if present
        for extra in ("outlier_transaction_count", "typical_volume_tzs"):
            if extra in feats:
                ml_features[extra] = float(feats[extra])
        ml_display = humanize_features(feats)
        outlier_count = int(feats.get("outlier_transaction_count") or 0)
        typical_vol = feats.get("typical_volume_tzs")
        details = get_predictor().predict_details(ml_features)
        probability = details.get("probability_creditworthy")
        model_version = details.get("model_version") or model_version
        primary_model = details.get("primary_model")
        if score is None:
            score = details.get("score")

    ml_summary = None
    if not score_eligible:
        needed = max(0, settings.min_transactions_for_score - tx_count)
        ml_summary = (
            f"ML scoring locked until this SME records at least "
            f"{settings.min_transactions_for_score} transactions "
            f"({needed} more needed). Metrics use this SME’s own supply-chain feed."
        )
    elif latest or ml_features:
        ml_summary = (
            "These ML metrics are computed from this SME’s uploaded / recorded "
            "transactions only (payment behaviour, value-chain roles, delays)."
        )

    return SMEDetailResponse(
        sme_profile_id=profile.id,
        display_token=profile.display_token,
        business_type=profile.business_type,
        nida=profile.nida,
        full_name=user.full_name if user else "",
        phone=profile.phone,
        email=profile.email,
        tin=profile.tin,
        location=profile.location,
        nationality=profile.nationality,
        date_of_birth=profile.date_of_birth,
        transaction_count=tx_count,
        total_volume_tzs=round(total_volume, 2),
        latest_score=score,
        risk_band=risk,
        eligible_financing_tzs=eligible,
        monthly_history=[MonthlyHistoryResponse.model_validate(h) for h in history],
        score_locked=not score_eligible or score is None,
        transactions_needed=max(0, settings.min_transactions_for_score - tx_count),
        model_version=model_version,
        primary_model=primary_model,
        probability_creditworthy=probability,
        ml_features=ml_features,
        ml_features_display=ml_display,
        outlier_transaction_count=outlier_count,
        typical_volume_tzs=typical_vol,
        ml_summary=ml_summary,
    )
