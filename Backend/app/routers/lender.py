from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.database import get_db
from app.dependencies import RequireLender
from app.models import LenderProfile, SMEProfile, Transaction, User
from app.schemas.auth import LenderProfileResponse, LenderProfileUpdateRequest
from app.schemas.dashboard import DashboardSummary, SMEDetailResponse, SMEPortfolioItem
from app.schemas.transaction import TransactionResponse
from app.services.auth_service import update_lender_profile
from app.services.csv_export import export_estatement_for_profile
from app.services.dashboard_service import lender_dashboard, lender_portfolio, lender_sme_detail

router = APIRouter(prefix="/lender", tags=["Lender"])


def _lender_profile_response(profile: LenderProfile, user: User) -> LenderProfileResponse:
    return LenderProfileResponse(
        membership_number=profile.membership_number,
        full_name=user.full_name,
        gender=user.gender,
        organization=profile.organization,
        work_email=profile.work_email,
        phone=profile.phone,
        login_id=user.login_id,
    )


@router.get("/profile", response_model=LenderProfileResponse)
def get_lender_profile(current_user: RequireLender, db: Session = Depends(get_db)):
    profile = db.query(LenderProfile).filter(LenderProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lender profile not found")
    return _lender_profile_response(profile, current_user)


@router.put("/profile", response_model=LenderProfileResponse)
def put_lender_profile(
    payload: LenderProfileUpdateRequest,
    current_user: RequireLender,
    db: Session = Depends(get_db),
):
    profile = update_lender_profile(db, current_user, payload)
    return _lender_profile_response(profile, current_user)


@router.get("/dashboard", response_model=DashboardSummary)
def dashboard(current_user: RequireLender, db: Session = Depends(get_db)):
    return lender_dashboard(db)


@router.get("/portfolio", response_model=list[SMEPortfolioItem])
def portfolio(
    current_user: RequireLender,
    db: Session = Depends(get_db),
    q: str | None = Query(default=None),
    risk: str | None = Query(default=None),
    min_score: float | None = Query(default=None),
    max_score: float | None = Query(default=None),
):
    return lender_portfolio(db, q=q, risk=risk, min_score=min_score, max_score=max_score)


@router.get("/sme/by-nida/{nida}", response_model=SMEDetailResponse)
def sme_by_nida(nida: str, current_user: RequireLender, db: Session = Depends(get_db)):
    profile = db.query(SMEProfile).filter(SMEProfile.nida == nida).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SME not found")
    detail = lender_sme_detail(db, profile.id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SME not found")
    return detail


@router.get("/sme/{sme_profile_id}", response_model=SMEDetailResponse)
def sme_detail(sme_profile_id: int, current_user: RequireLender, db: Session = Depends(get_db)):
    detail = lender_sme_detail(db, sme_profile_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SME not found")
    return detail


@router.get("/sme/{sme_profile_id}/transactions", response_model=list[TransactionResponse])
def sme_transactions(
    sme_profile_id: int,
    current_user: RequireLender,
    db: Session = Depends(get_db),
):
    profile = db.query(SMEProfile).filter(SMEProfile.id == sme_profile_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SME not found")
    return (
        db.query(Transaction)
        .filter(Transaction.sme_profile_id == profile.id)
        .order_by(Transaction.transaction_date.desc())
        .all()
    )


@router.get("/sme/{sme_profile_id}/statement")
def sme_statement(
    sme_profile_id: int,
    current_user: RequireLender,
    db: Session = Depends(get_db),
):
    profile = db.query(SMEProfile).filter(SMEProfile.id == sme_profile_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SME not found")
    csv_content = export_estatement_for_profile(db, profile.id)
    filename = f"sme_{profile.display_token}_statement.csv"
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
