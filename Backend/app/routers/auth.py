from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.auth import (
    ChangePinRequest,
    LoginRequest,
    SMERegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import change_pin, login_user, register_sme

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(payload: SMERegisterRequest, db: Session = Depends(get_db)):
    user = register_sme(db, payload)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return login_user(db, payload.login_id, payload.pin)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/change-pin")
def change_own_pin(
    payload: ChangePinRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    change_pin(db, current_user, payload.current_pin, payload.new_pin)
    return {"message": "PIN changed successfully"}
