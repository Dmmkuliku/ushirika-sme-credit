import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import CreditScore, SMEProfile, Transaction, User
from app.schemas.credit import FeatureVector
from app.services.feature_engineering import compute_features
from app.services.ml_predictor import get_predictor


def risk_band_from_score(score: float) -> str:
    # Bands aligned with conservative score mapping (~300–680).
    if score >= 580:
        return "low"
    if score >= 480:
        return "medium"
    return "high"


def financing_from_score(score: float, total_volume_tzs: float) -> float:
    settings = get_settings()
    normalized = max(0.0, min(1.0, (score - 300) / 500))
    raw_amount = settings.min_financing_tzs + normalized * (settings.max_financing_tzs - settings.min_financing_tzs)
    cap = total_volume_tzs * 0.75
    return round(min(raw_amount, cap), 2)


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

    total_volume = sum(t.amount_tzs for t in transactions)

    if not force_refresh:
        latest = (
            db.query(CreditScore)
            .filter(CreditScore.user_id == user.id)
            .order_by(CreditScore.created_at.desc())
            .first()
        )
        if latest:
            features = FeatureVector(**json.loads(latest.features_json))
            return {
                "eligible": True,
                "transaction_count": tx_count,
                "transactions_needed": 0,
                "credit_score": latest,
                "features": features,
                "cached": True,
            }

    features_dict = compute_features(transactions, profile.date_of_birth.year)
    features = FeatureVector(**features_dict)

    predictor = get_predictor()
    ml_score, model_version = predictor.predict_credit_score(features_dict)

    risk_band = risk_band_from_score(ml_score)
    financing = financing_from_score(ml_score, total_volume)

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
        "cached": False,
    }
