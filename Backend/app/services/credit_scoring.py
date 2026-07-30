import json
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
    if score >= 650:
        return "low"
    if score >= 500:
        return "medium"
    return "high"


def financing_from_prediction(
    score: float,
    probability: float,
    amounts: list[float],
    features: dict[str, float] | None = None,
) -> tuple[float, dict]:
    """
    Indicative financing predicted from repayment and trading patterns.

    The estimate is driven by model probability, score, on-time behaviour,
    growth, frequency and typical deal size. It is allowed to exceed the SME's
    historical total money moved when the pattern supports higher capacity —
    only the system max ceiling still applies.
    """
    settings = get_settings()
    caps = robust_volume_and_caps(amounts)
    features = features or {}

    typical = float(caps.get("typical_volume_tzs") or 0.0)
    total_volume = float(caps.get("total_volume_tzs") or typical)
    median_amt = float(caps.get("median_typical_amount_tzs") or 0.0)
    proba = max(0.0, min(1.0, float(probability)))
    score_norm = max(0.0, min(1.0, (float(score) - 300.0) / 550.0))

    on_time = max(0.0, min(1.0, float(features.get("on_time_rate", proba))))
    consistency = max(0.0, min(1.0, float(features.get("payment_consistency", proba))))
    default_rate = max(0.0, min(1.0, float(features.get("default_rate", 0.0))))
    compliance = max(0.0, min(1.0, float(features.get("compliance_rate", on_time))))
    frequency = max(0.0, float(features.get("transaction_frequency", 0.0)))
    trend_raw = float(features.get("volume_trend", 0.0))
    trend = max(0.0, min(1.0, 0.5 + 0.5 * max(-1.0, min(1.0, trend_raw))))

    behaviour = (
        0.35 * on_time
        + 0.25 * consistency
        + 0.20 * (1.0 - default_rate)
        + 0.10 * compliance
        + 0.10 * trend
    )
    model_strength = 0.55 * proba + 0.45 * score_norm
    pattern = 0.55 * model_strength + 0.45 * behaviour

    # Pattern multiplier on historical volume: weak ~0.35x, strong up to ~2.4x
    # so strong SMEs can be offered more than total money already moved.
    volume_multiplier = 0.35 + 2.05 * pattern

    # Deal-capacity view: how many median-sized deals the pattern supports.
    deal_count = 2.0 + 14.0 * pattern  # about 2–16 typical deals
    freq_boost = 1.0 + min(1.0, frequency / 8.0) * 0.35  # active traders get a lift
    from_deals = median_amt * deal_count * freq_boost if median_amt > 0 else 0.0
    from_volume = (typical if typical > 0 else total_volume) * volume_multiplier

    candidates = [v for v in (from_volume, from_deals) if v > 0]
    if not candidates:
        return 0.0, caps

    # Blend both pattern views (not the minimum — prediction, not a hard history cap).
    financing = 0.55 * max(candidates) + 0.45 * (sum(candidates) / len(candidates))

    # Absolute product ceiling only — do NOT force below total money moved.
    financing = min(financing, float(settings.max_financing_tzs))

    # Soft floor from pattern + volume when history exists (not a flat 500k).
    base = typical if typical > 0 else total_volume
    if base > 0:
        soft_floor = base * (0.20 + 0.40 * pattern)
        financing = max(financing, soft_floor)

    return round(max(0.0, financing), 2), caps


# Backwards-compatible alias used by older call sites / tests.
def financing_from_score(score: float, amounts: list[float]) -> tuple[float, dict]:
    normalized = max(0.0, min(1.0, (score - 300) / 550))
    return financing_from_prediction(score, normalized, amounts, features=None)


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
    _, caps = financing_from_prediction(300, 0.5, amounts, features_dict)
    features_dict["outlier_transaction_count"] = float(caps["outlier_transaction_count"])
    features_dict["typical_volume_tzs"] = float(caps["typical_volume_tzs"])

    ml_features = {k: float(features_dict.get(k, 0.0)) for k in FEATURE_COLUMNS}
    features = FeatureVector(**ml_features)

    predictor = get_predictor()
    details = predictor.predict_details(ml_features)
    ml_score = float(details["score"])
    model_version = str(details["model_version"])
    probability = float(details.get("probability_creditworthy") or 0.5)

    risk_band = risk_band_from_score(ml_score)
    financing, caps = financing_from_prediction(
        ml_score,
        probability,
        amounts,
        features=features_dict,
    )
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
        "probability_creditworthy": probability,
        "cached": False,
    }
