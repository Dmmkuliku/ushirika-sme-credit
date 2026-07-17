from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import RequireAdmin, RequireLenderOrAdmin, RequireSME, get_current_user
from app.models import User, UserRole
from app.schemas.dashboard import DashboardSummary, SMEDashboardSummary
from app.services.dashboard_service import lender_dashboard, sme_dashboard

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/sme", response_model=SMEDashboardSummary)
def sme_summary(current_user: RequireSME, db: Session = Depends(get_db)):
    return sme_dashboard(db, current_user)


@router.get("/lender", response_model=DashboardSummary)
def lender_summary(current_user: RequireLenderOrAdmin, db: Session = Depends(get_db)):
    return lender_dashboard(db)
