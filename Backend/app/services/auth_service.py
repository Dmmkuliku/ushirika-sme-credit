from datetime import date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import LenderProfile, SMEProfile, User, UserRole
from app.schemas.auth import LenderCreateRequest, SMERegisterRequest, SubAdminCreateRequest
from app.utils.pseudonymization import generate_display_token
from app.utils.security import create_access_token, hash_pin, verify_pin


def register_sme(db: Session, payload: SMERegisterRequest) -> User:
    existing = db.query(User).filter(User.login_id == payload.nida).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="NIDA already registered")

    user = User(
        login_id=payload.nida,
        hashed_pin=hash_pin(payload.pin),
        role=UserRole.SME,
        full_name=payload.full_name,
        gender=payload.gender,
    )
    db.add(user)
    db.flush()

    profile = SMEProfile(
        user_id=user.id,
        nida=payload.nida,
        phone=payload.phone,
        email=payload.email,
        location=payload.location,
        nationality=payload.nationality,
        date_of_birth=date.fromisoformat(payload.date_of_birth),
        business_type=payload.business_type,
        tin=payload.tin,
        display_token=generate_display_token(),
    )
    db.add(profile)
    db.commit()
    db.refresh(user)
    return user


def create_lender(db: Session, payload: LenderCreateRequest) -> User:
    existing = db.query(User).filter(User.login_id == payload.membership_number).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Membership number already registered")

    user = User(
        login_id=payload.membership_number,
        hashed_pin=hash_pin(payload.pin),
        role=UserRole.LENDER,
        full_name=payload.full_name,
        gender=payload.gender,
    )
    db.add(user)
    db.flush()

    profile = LenderProfile(
        user_id=user.id,
        membership_number=payload.membership_number,
        organization=payload.organization,
        work_email=payload.work_email,
        phone=payload.phone,
    )
    db.add(profile)
    db.commit()
    db.refresh(user)
    return user


def create_subadmin(db: Session, payload: SubAdminCreateRequest) -> User:
    existing = db.query(User).filter(User.login_id == payload.login_id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Login ID already registered")

    user = User(
        login_id=payload.login_id,
        hashed_pin=hash_pin(payload.pin),
        role=UserRole.SUBADMIN,
        full_name=payload.full_name,
        gender=payload.gender,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, login_id: str, pin: str) -> User | None:
    user = db.query(User).filter(User.login_id == login_id).first()
    if not user or not verify_pin(pin, user.hashed_pin):
        return None
    if not user.is_active:
        return None
    return user


def login_user(db: Session, login_id: str, pin: str) -> dict:
    user = authenticate_user(db, login_id, pin)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = get_settings()
    expires = timedelta(minutes=settings.access_token_expire_minutes)
    token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value},
        expires_delta=expires,
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": int(expires.total_seconds()),
        "role": user.role.value,
        "user": user,
    }


def change_pin(db: Session, user: User, current_pin: str, new_pin: str) -> None:
    if not verify_pin(current_pin, user.hashed_pin):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current PIN is incorrect",
        )
    if current_pin == new_pin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New PIN must be different from current PIN",
        )
    user.hashed_pin = hash_pin(new_pin)
    db.commit()


def reset_pin_with_birthdate(db: Session, login_id: str, date_of_birth: str, new_pin: str) -> None:
    """Allow PIN reset when birthdate matches the SME registration record."""
    user = db.query(User).filter(User.login_id == login_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    if user.role != UserRole.SME:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PIN recovery with birthdate is available for SME accounts. Contact your administrator for other roles.",
        )

    profile = db.query(SMEProfile).filter(SMEProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SME profile not found")

    try:
        dob = date.fromisoformat(date_of_birth)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date of birth")

    if profile.date_of_birth != dob:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date of birth does not match our records",
        )

    user.hashed_pin = hash_pin(new_pin)
    db.commit()


def update_sme_profile(db: Session, user: User, payload) -> SMEProfile:
    profile = db.query(SMEProfile).filter(SMEProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SME profile not found")

    data = payload.model_dump(exclude_unset=True)
    if "full_name" in data and data["full_name"] is not None:
        user.full_name = data.pop("full_name")
    if "gender" in data and data["gender"] is not None:
        user.gender = data.pop("gender")
    for field, value in data.items():
        if value is not None and hasattr(profile, field):
            setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile


def update_lender_profile(db: Session, user: User, payload) -> LenderProfile:
    profile = db.query(LenderProfile).filter(LenderProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lender profile not found")

    data = payload.model_dump(exclude_unset=True)
    if "full_name" in data and data["full_name"] is not None:
        user.full_name = data.pop("full_name")
    if "gender" in data and data["gender"] is not None:
        user.gender = data.pop("gender")
    for field, value in data.items():
        if value is not None and hasattr(profile, field):
            setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile


def update_admin_self(db: Session, user: User, payload) -> User:
    data = payload.model_dump(exclude_unset=True)
    if "full_name" in data and data["full_name"] is not None:
        user.full_name = data["full_name"]
    if "gender" in data and data["gender"] is not None:
        user.gender = data["gender"]
    db.commit()
    db.refresh(user)
    return user
