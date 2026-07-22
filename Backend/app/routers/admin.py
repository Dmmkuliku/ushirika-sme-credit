import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.database import get_db
from app.dependencies import RequireAdmin, RequireAdminOrSubAdmin
from app.models import LenderProfile, ModelMetrics, SMEProfile, User, UserRole
from app.schemas.auth import (
    AdminSelfUpdateRequest,
    LenderCreateRequest,
    SMERegisterRequest,
    SubAdminCreateRequest,
    UserResponse,
    _normalize_tz_phone,
    _require_tanzania_region,
    _require_valid_email,
)
from app.tanzania_geo import require_district_in_region
from app.schemas.credit import ModelMetricsResponse, TrainingResultResponse
from app.schemas.health import HealthResponse
from app.services.auth_service import create_lender, create_subadmin, register_sme, update_admin_self
from app.services.ml_predictor import get_predictor, reload_predictor
from app.services.ml_training import train_models
from app.utils.security import hash_pin

router = APIRouter(tags=["Admin & Health"])


class AdminAccountListItem(BaseModel):
    id: int
    login_id: str
    full_name: str
    role: str
    gender: str
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class AdminAccountDetail(BaseModel):
    id: int
    login_id: str
    full_name: str
    role: str
    gender: str
    is_active: bool
    created_at: datetime
    nida: str | None = None
    phone: str | None = None
    email: str | None = None
    location: str | None = None
    district: str | None = None
    business_type: str | None = None
    nationality: str | None = None
    date_of_birth: str | None = None
    display_token: str | None = None
    membership_number: str | None = None
    organization: str | None = None
    work_email: str | None = None


class AccountUpdateRequest(BaseModel):
    full_name: str | None = None
    gender: str | None = None
    is_active: bool | None = None
    organization: str | None = None
    work_email: str | None = None
    phone: str | None = None
    location: str | None = None
    district: str | None = None
    business_type: str | None = None
    email: str | None = None

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str | None) -> str | None:
        if v is not None and v not in ("Male", "Female"):
            raise ValueError("gender must be Male or Female")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        return _normalize_tz_phone(v)

    @field_validator("location")
    @classmethod
    def validate_location(cls, v: str | None) -> str | None:
        return _require_tanzania_region(v)

    @field_validator("email", "work_email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        return _require_valid_email(v)

    @model_validator(mode="after")
    def validate_district_matches_region(self):
        if self.district is not None:
            if self.location is None:
                raise ValueError("region is required when updating district")
            require_district_in_region(self.location, self.district)
        return self


class ResetPinRequest(BaseModel):
    pin: str

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, v: str) -> str:
        if not re.match(r"^\d{4}$", v):
            raise ValueError("PIN must be exactly 4 digits")
        return v


def _build_detail(user: User) -> AdminAccountDetail:
    d = AdminAccountDetail(
        id=user.id,
        login_id=user.login_id,
        full_name=user.full_name,
        role=user.role.value,
        gender=user.gender,
        is_active=user.is_active,
        created_at=user.created_at,
    )
    if user.sme_profile:
        p = user.sme_profile
        d.nida = p.nida
        d.phone = p.phone
        d.email = p.email
        d.location = p.location
        d.district = p.district
        d.business_type = p.business_type
        d.nationality = p.nationality
        d.date_of_birth = str(p.date_of_birth)
        d.display_token = p.display_token
    if user.lender_profile:
        lp = user.lender_profile
        d.membership_number = lp.membership_number
        d.organization = lp.organization
        d.work_email = lp.work_email
        d.phone = lp.phone
    return d


@router.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    predictor = get_predictor()
    return HealthResponse(
        status="healthy" if db_status == "ok" else "degraded",
        version=__version__,
        timestamp=datetime.now(timezone.utc),
        database=db_status,
        model_loaded=predictor.is_loaded,
    )


@router.post("/admin/train-model", response_model=TrainingResultResponse, tags=["Admin"])
def train_model_endpoint(current_user: RequireAdmin, db: Session = Depends(get_db)):
    results = train_models(db_session=db)
    reload_predictor()

    models = [
        ModelMetricsResponse(
            model_name=results["rf_metrics"]["model_name"],
            model_version=results["version"],
            accuracy=results["rf_metrics"]["accuracy"],
            precision_score=results["rf_metrics"]["precision_score"],
            recall=results["rf_metrics"]["recall"],
            f1=results["rf_metrics"]["f1"],
            roc_auc=results["rf_metrics"]["roc_auc"],
            is_primary=True,
            trained_at=datetime.now(timezone.utc),
        ),
        ModelMetricsResponse(
            model_name=results["lr_metrics"]["model_name"],
            model_version=results["version"],
            accuracy=results["lr_metrics"]["accuracy"],
            precision_score=results["lr_metrics"]["precision_score"],
            recall=results["lr_metrics"]["recall"],
            f1=results["lr_metrics"]["f1"],
            roc_auc=results["lr_metrics"]["roc_auc"],
            is_primary=False,
            trained_at=datetime.now(timezone.utc),
        ),
    ]

    msg = "Training complete."
    if results["rf_outperforms_baseline"]:
        msg += " Random Forest ROC-AUC >= Logistic Regression baseline."
    else:
        msg += " Warning: baseline matched or exceeded RF on hold-out set."

    return TrainingResultResponse(
        primary_model="random_forest",
        models=models,
        rf_outperforms_baseline=results["rf_outperforms_baseline"],
        message=msg,
    )


@router.get("/admin/model-metrics", response_model=list[ModelMetricsResponse], tags=["Admin"])
def get_model_metrics(current_user: RequireAdmin, db: Session = Depends(get_db)):
    metrics = db.query(ModelMetrics).order_by(ModelMetrics.trained_at.desc()).limit(10).all()
    return metrics


@router.get("/admin/model-meta", tags=["Admin"])
def get_model_meta(current_user: RequireAdmin):
    """Full training meta: metrics, confusion matrices, preprocessing, feature importance."""
    from pathlib import Path

    from app.config import get_settings

    meta_path = Path(get_settings().model_dir) / "model_meta.json"
    if not meta_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No trained model meta found")
    import json

    with open(meta_path, encoding="utf-8") as f:
        return json.load(f)


@router.post("/admin/run-eda", tags=["Admin"])
def run_eda_endpoint(current_user: RequireAdmin, db: Session = Depends(get_db)):
    """Generate Seaborn/Plotly EDA figures (proposal §3.7)."""
    from app.services.eda import run_eda

    return run_eda(db_session=db)


@router.get("/admin/accounts", response_model=list[AdminAccountListItem], tags=["Admin"])
def list_accounts(
    current_user: RequireAdminOrSubAdmin,
    db: Session = Depends(get_db),
    role: str | None = Query(default=None),
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == UserRole(role))
    return query.order_by(User.id).all()


@router.get("/admin/accounts/{user_id}", response_model=AdminAccountDetail, tags=["Admin"])
def get_account(user_id: int, current_user: RequireAdminOrSubAdmin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _build_detail(user)


@router.post("/admin/accounts/lender", response_model=UserResponse, status_code=201, tags=["Admin"])
def create_lender_account(payload: LenderCreateRequest, current_user: RequireAdminOrSubAdmin, db: Session = Depends(get_db)):
    return create_lender(db, payload)


@router.post("/admin/accounts/subadmin", response_model=UserResponse, status_code=201, tags=["Admin"])
def create_subadmin_account(payload: SubAdminCreateRequest, current_user: RequireAdmin, db: Session = Depends(get_db)):
    return create_subadmin(db, payload)


@router.post("/admin/accounts/sme", response_model=UserResponse, status_code=201, tags=["Admin"])
def create_sme_account(payload: SMERegisterRequest, current_user: RequireAdminOrSubAdmin, db: Session = Depends(get_db)):
    return register_sme(db, payload)


@router.put("/admin/accounts/{user_id}", response_model=AdminAccountDetail, tags=["Admin"])
def update_account(user_id: int, payload: AccountUpdateRequest, current_user: RequireAdminOrSubAdmin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.gender is not None:
        user.gender = payload.gender
    if payload.is_active is not None:
        user.is_active = payload.is_active

    if user.sme_profile:
        if payload.location is not None:
            user.sme_profile.location = payload.location
        if payload.district is not None:
            user.sme_profile.district = payload.district
        if payload.business_type is not None:
            user.sme_profile.business_type = payload.business_type
        if payload.email is not None:
            user.sme_profile.email = payload.email
        if payload.phone is not None:
            user.sme_profile.phone = payload.phone

    if user.lender_profile:
        if payload.organization is not None:
            user.lender_profile.organization = payload.organization
        if payload.work_email is not None:
            user.lender_profile.work_email = payload.work_email
        if payload.phone is not None:
            user.lender_profile.phone = payload.phone

    db.commit()
    db.refresh(user)
    return _build_detail(user)


@router.delete("/admin/accounts/{user_id}", tags=["Admin"])
def delete_account(user_id: int, current_user: RequireAdminOrSubAdmin, db: Session = Depends(get_db)):
    """Permanently delete a user account and related profile/transaction data."""
    from app.models import CreditScore, MonthlyHistory, Transaction

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )
    if user.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrator accounts cannot be deleted here",
        )

    db.query(CreditScore).filter(CreditScore.user_id == user.id).delete(synchronize_session=False)

    if user.sme_profile:
        profile_id = user.sme_profile.id
        db.query(Transaction).filter(Transaction.sme_profile_id == profile_id).delete(
            synchronize_session=False
        )
        db.query(MonthlyHistory).filter(MonthlyHistory.sme_profile_id == profile_id).delete(
            synchronize_session=False
        )
        db.delete(user.sme_profile)

    if user.lender_profile:
        db.delete(user.lender_profile)

    db.delete(user)
    db.commit()
    return {"detail": "Account permanently deleted"}


@router.put("/admin/accounts/{user_id}/reset-pin", tags=["Admin"])
def reset_pin(user_id: int, payload: ResetPinRequest, current_user: RequireAdminOrSubAdmin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.hashed_pin = hash_pin(payload.pin)
    db.commit()
    return {"detail": "PIN reset successfully"}


@router.get("/admin/profile", response_model=UserResponse, tags=["Admin"])
def get_own_admin_profile(current_user: RequireAdminOrSubAdmin):
    return current_user


@router.put("/admin/profile", response_model=UserResponse, tags=["Admin"])
def update_own_admin_profile(
    payload: AdminSelfUpdateRequest,
    current_user: RequireAdminOrSubAdmin,
    db: Session = Depends(get_db),
):
    return update_admin_self(db, current_user, payload)
