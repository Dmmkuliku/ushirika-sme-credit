from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import RequireSME
from app.models import SMEProfile
from app.schemas.auth import SMEProfileResponse, SMEProfileUpdateRequest, UserResponse
from app.services.auth_service import update_sme_profile

router = APIRouter(prefix="/sme", tags=["SME"])


def _sme_profile_response(profile: SMEProfile, user) -> SMEProfileResponse:
    return SMEProfileResponse(
        id=profile.id,
        nida=profile.nida,
        phone=profile.phone,
        email=profile.email,
        location=profile.location,
        business_type=profile.business_type,
        nationality=profile.nationality,
        date_of_birth=profile.date_of_birth,
        tin=profile.tin,
        display_token=profile.display_token,
        full_name=user.full_name,
        gender=user.gender,
        created_at=profile.created_at,
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: RequireSME):
    return current_user


@router.get("/profile", response_model=SMEProfileResponse)
def get_profile(current_user: RequireSME, db: Session = Depends(get_db)):
    profile = db.query(SMEProfile).filter(SMEProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SME profile not found")
    return _sme_profile_response(profile, current_user)


@router.put("/profile", response_model=SMEProfileResponse)
def put_profile(
    payload: SMEProfileUpdateRequest,
    current_user: RequireSME,
    db: Session = Depends(get_db),
):
    profile = update_sme_profile(db, current_user, payload)
    return _sme_profile_response(profile, current_user)
