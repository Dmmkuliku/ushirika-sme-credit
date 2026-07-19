"""Score SME quickly after data changes; optional background retrain (non-blocking)."""
from __future__ import annotations

import logging
import threading
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Transaction
from app.services.credit_scoring import score_sme
from app.services.ml_predictor import get_predictor

logger = logging.getLogger(__name__)
_retrain_lock = threading.Lock()


def score_after_data_change(db: Session, user) -> dict[str, Any]:
    """
    Fast path used after create/import/update/delete:
    refresh credit score with the current Random Forest model (same model lenders see).
    Does NOT run GridSearchCV in-request (that caused upload timeouts).
    """
    settings = get_settings()
    from app.models import SMEProfile

    profile = db.query(SMEProfile).filter(SMEProfile.user_id == user.id).first()
    if not profile:
        return {"score_ready": False, "reason": "no_profile"}

    tx_count = db.query(Transaction).filter(Transaction.sme_profile_id == profile.id).count()
    needed = max(0, settings.min_transactions_for_score - tx_count)
    if tx_count < settings.min_transactions_for_score:
        return {
            "score_ready": False,
            "transaction_count": tx_count,
            "transactions_needed": needed,
            "message": (
                f"Need at least {settings.min_transactions_for_score} transactions "
                f"before a credit score can be produced ({needed} more)."
            ),
        }

    try:
        result = score_sme(db, user, force_refresh=True)
    except Exception as exc:
        logger.exception("Scoring failed after data change: %s", exc)
        return {
            "score_ready": False,
            "transaction_count": tx_count,
            "transactions_needed": 0,
            "message": f"Could not compute score yet: {exc}",
        }

    if not result.get("eligible"):
        return {
            "score_ready": False,
            "transaction_count": tx_count,
            "transactions_needed": result.get("transactions_needed", needed),
            "message": result.get("message") or "Score not ready",
        }

    cs = result["credit_score"]
    predictor = get_predictor()
    feats = result.get("features")
    feat_dict = feats.model_dump() if hasattr(feats, "model_dump") else dict(feats or {})
    details = predictor.predict_details(feat_dict)

    return {
        "score_ready": True,
        "transaction_count": tx_count,
        "transactions_needed": 0,
        "score": float(cs.score),
        "risk_band": cs.risk_band,
        "eligible_financing_tzs": float(cs.eligible_financing_tzs),
        "model_version": cs.model_version,
        "primary_model": details.get("primary_model") or "random_forest",
        "probability_creditworthy": details.get("probability_creditworthy"),
        "ml_features_display": result.get("features_display") or [],
        "message": "ML credit assessment ready from your uploaded transactions.",
    }


def schedule_background_retrain(db_url_hint: str | None = None) -> None:
    """Fire-and-forget model refresh so future scores use latest SME mix (non-blocking)."""
    if not _retrain_lock.acquire(blocking=False):
        logger.info("Background retrain already running — skip")
        return

    def _job():
        try:
            from app.database import SessionLocal
            from app.services.ml_training import retrain_after_sme_data_change

            session = SessionLocal()
            try:
                retrain_after_sme_data_change(session)
                logger.info("Background retrain finished")
            finally:
                session.close()
        except Exception:
            logger.exception("Background retrain failed")
        finally:
            _retrain_lock.release()

    threading.Thread(target=_job, name="ushirika-retrain", daemon=True).start()
