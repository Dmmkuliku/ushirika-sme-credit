from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.limiter import limiter
from app.models import User
from app.schemas.auth import (
    ChangePinRequest,
    ForgotPinRequest,
    LoginRequest,
    SMERegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import change_pin, login_user, register_sme, reset_pin_with_birthdate

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("5/minute")
def register(
    request: Request,
    response: Response,
    payload: SMERegisterRequest,
    db: Session = Depends(get_db),
):
    user = register_sme(db, payload)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    return login_user(db, payload.login_id, payload.pin)


@router.post("/forgot-pin")
@limiter.limit("5/minute")
def forgot_pin(
    request: Request,
    response: Response,
    payload: ForgotPinRequest,
    db: Session = Depends(get_db),
):
    reset_pin_with_birthdate(
        db, payload.login_id, payload.date_of_birth, payload.phone, payload.new_pin
    )
    return {"message": "PIN reset successfully. You can now sign in with your new PIN."}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/change-pin")
@limiter.limit("10/minute")
def change_own_pin(
    request: Request,
    response: Response,
    payload: ChangePinRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    change_pin(db, current_user, payload.current_pin, payload.new_pin)
    return {"message": "PIN changed successfully"}
