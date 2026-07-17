from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import RequireSME
from app.models import CreditScore
from app.schemas.credit import CreditScoreRequest, CreditScoreResponse, FeatureVector
from app.services.credit_scoring import score_sme
from app.services.monthly_history import get_monthly_history, refresh_monthly_history
from app.models import SMEProfile

router = APIRouter(prefix="/credit", tags=["Credit Scoring"])


@router.post("/score", response_model=CreditScoreResponse)
def request_credit_score(
    payload: CreditScoreRequest,
    current_user: RequireSME,
    db: Session = Depends(get_db),
):
    result = score_sme(db, current_user, force_refresh=payload.force_refresh)
    if not result["eligible"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"],
        )

    cs: CreditScore = result["credit_score"]
    features: FeatureVector = result["features"]
    return CreditScoreResponse(
        id=cs.id,
        score=cs.score,
        risk_band=cs.risk_band,
        eligible_financing_tzs=cs.eligible_financing_tzs,
        model_version=cs.model_version,
        features=features,
        created_at=cs.created_at,
        transaction_count=result["transaction_count"],
        eligible=True,
    )


@router.get("/score/latest", response_model=CreditScoreResponse)
def get_latest_score(current_user: RequireSME, db: Session = Depends(get_db)):
    latest = (
        db.query(CreditScore)
        .filter(CreditScore.user_id == current_user.id)
        .order_by(CreditScore.created_at.desc())
        .first()
    )
    if not latest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No credit score found")

    import json

    tx_count = (
        db.query(SMEProfile)
        .filter(SMEProfile.user_id == current_user.id)
        .first()
    )
    from app.models import Transaction

    profile = tx_count
    count = 0
    if profile:
        count = db.query(Transaction).filter(Transaction.sme_profile_id == profile.id).count()

    return CreditScoreResponse(
        id=latest.id,
        score=latest.score,
        risk_band=latest.risk_band,
        eligible_financing_tzs=latest.eligible_financing_tzs,
        model_version=latest.model_version,
        features=FeatureVector(**json.loads(latest.features_json)),
        created_at=latest.created_at,
        transaction_count=count,
        eligible=True,
    )


@router.get("/history/monthly")
def monthly_history(current_user: RequireSME, db: Session = Depends(get_db)):
    profile = db.query(SMEProfile).filter(SMEProfile.user_id == current_user.id).first()
    if profile:
        refresh_monthly_history(db, profile.id)
    history = get_monthly_history(db, current_user.id)
    return [
        {
            "year_month": h.year_month,
            "total_volume_tzs": h.total_volume_tzs,
            "transaction_count": h.transaction_count,
            "avg_delay_days": h.avg_delay_days,
            "on_time_rate": h.on_time_rate,
            "default_count": h.default_count,
            "compliance_rate": h.compliance_rate,
        }
        for h in history
    ]
