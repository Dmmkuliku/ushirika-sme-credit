import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import CreditScore, SMEProfile, Transaction, User
from app.services.feature_engineering import FEATURE_COLUMNS, compute_features
from app.services.labels import humanize_features
from app.services.ml_predictor import get_predictor
from app.services.outliers import amount_outlier_mask, robust_volume_and_caps
from app.schemas.credit import FeatureVector


def risk_band_from_score(score: float) -> str:
    if score >= 580:
        return "low"
    if score >= 480:
        return "medium"
    return "high"


def financing_from_score(score: float, amounts: list[float]) -> tuple[float, dict]:
    """
    Realistic financing: score suggests capacity, but never above what the SME
    typically handles. One-off giant deals (outliers) do not inflate the loan.
    """
    settings = get_settings()
    caps = robust_volume_and_caps(amounts)
    normalized = max(0.0, min(1.0, (score - 300) / 500))
    raw_amount = settings.min_financing_tzs + normalized * (
        settings.max_financing_tzs - settings.min_financing_tzs
    )

    candidates = [raw_amount]
    if caps["cap_history_tzs"] > 0:
        candidates.append(float(caps["cap_history_tzs"]))
    if caps["cap_experience_tzs"] > 0:
        candidates.append(float(caps["cap_experience_tzs"]))

    # Absolute ceiling: never above half of typical trading history
    financing = round(max(0.0, min(candidates)), 2)
    hard_cap = float(caps["typical_volume_tzs"]) * 0.50 if caps["typical_volume_tzs"] else 0.0
    if hard_cap > 0:
        financing = min(financing, hard_cap)
    if amounts and financing < settings.min_financing_tzs:
        # Only raise to min if typical history can support it
        if float(caps["typical_volume_tzs"]) >= settings.min_financing_tzs:
            financing = min(float(settings.min_financing_tzs), hard_cap or float(settings.min_financing_tzs))
        else:
            financing = round(float(caps["typical_volume_tzs"]) * 0.50, 2)

    return round(financing, 2), caps


def _mark_outliers(db: Session, transactions: list[Transaction]) -> None:
    amounts = [t.amount_tzs for t in transactions]
    mask = amount_outlier_mask(amounts)
    dirty = False
    for tx, is_out in zip(transactions, mask):
        if bool(tx.is_outlier) != bool(is_out):
            tx.is_outlier = bool(is_out)
            dirty = True
    if dirty:
        db.commit()


def score_sme(
    db: Session,
    user: User,
    force_refresh: bool = False,
) -> dict[str, Any]:
    settings = get_settings()
    profile = db.query(SMEProfile).filter(SMEProfile.user_id == user.id).first()
    if not profile:
        raise ValueError("SME profile not found")

    transactions = (
        db.query(Transaction)
        .filter(Transaction.sme_profile_id == profile.id)
        .order_by(Transaction.transaction_date.asc())
        .all()
    )
    tx_count = len(transactions)

    if tx_count < settings.min_transactions_for_score:
        return {
            "eligible": False,
            "transaction_count": tx_count,
            "transactions_needed": settings.min_transactions_for_score - tx_count,
            "message": f"At least {settings.min_transactions_for_score} transactions required for scoring",
        }

    if not force_refresh:
        latest = (
            db.query(CreditScore)
            .filter(CreditScore.user_id == user.id)
            .order_by(CreditScore.created_at.desc())
            .first()
        )
        if latest:
            raw = json.loads(latest.features_json)
            ml_only = {k: float(raw.get(k, 0.0)) for k in FEATURE_COLUMNS}
            features = FeatureVector(**ml_only)
            return {
                "eligible": True,
                "transaction_count": tx_count,
                "transactions_needed": 0,
                "credit_score": latest,
                "features": features,
                "features_display": humanize_features(raw),
                "cached": True,
            }

    _mark_outliers(db, transactions)
    transactions = (
        db.query(Transaction)
        .filter(Transaction.sme_profile_id == profile.id)
        .order_by(Transaction.transaction_date.asc())
        .all()
    )

    features_dict = compute_features(transactions, profile.date_of_birth.year)
    amounts = [t.amount_tzs for t in transactions]
    _, caps = financing_from_score(300, amounts)
    features_dict["outlier_transaction_count"] = float(caps["outlier_transaction_count"])
    features_dict["typical_volume_tzs"] = float(caps["typical_volume_tzs"])

    ml_features = {k: float(features_dict.get(k, 0.0)) for k in FEATURE_COLUMNS}
    features = FeatureVector(**ml_features)

    predictor = get_predictor()
    ml_score, model_version = predictor.predict_credit_score(ml_features)

    risk_band = risk_band_from_score(ml_score)
    financing, caps = financing_from_score(ml_score, amounts)
    features_dict["outlier_transaction_count"] = float(caps["outlier_transaction_count"])
    features_dict["typical_volume_tzs"] = float(caps["typical_volume_tzs"])

    credit_score = CreditScore(
        user_id=user.id,
        score=ml_score,
        risk_band=risk_band,
        eligible_financing_tzs=financing,
        model_version=model_version,
        features_json=json.dumps(features_dict),
    )
    db.add(credit_score)
    db.commit()
    db.refresh(credit_score)

    return {
        "eligible": True,
        "transaction_count": tx_count,
        "transactions_needed": 0,
        "credit_score": credit_score,
        "features": features,
        "features_display": humanize_features(features_dict),
        "outlier_transaction_count": caps["outlier_transaction_count"],
        "typical_volume_tzs": caps["typical_volume_tzs"],
        "cached": False,
    }
