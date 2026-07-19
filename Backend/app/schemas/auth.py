import re
from datetime import datetime, date

from pydantic import BaseModel, Field, field_validator


_PIN_RE = re.compile(r"^\d{4}$")
_NIDA_RE = re.compile(r"^\d{20}$")
_TIN_RE = re.compile(r"^\d{9}$")


class SMERegisterRequest(BaseModel):
    nida: str = Field(min_length=20, max_length=20, description="Exactly 20 digits")
    phone: str = Field(min_length=10, max_length=20)
    full_name: str = Field(min_length=2, max_length=200)
    email: str | None = Field(default=None, max_length=254)
    location: str = Field(min_length=2, max_length=200)
    business_type: str = Field(min_length=2, max_length=100)
    gender: str
    nationality: str = Field(default="Tanzanian", max_length=50)
    date_of_birth: str
    tin: str = Field(min_length=9, max_length=9, description="Tax Identification Number — exactly 9 digits")
    pin: str

    @field_validator("nida")
    @classmethod
    def validate_nida(cls, v: str) -> str:
        digits = "".join(ch for ch in str(v).strip() if ch.isdigit())
        if not _NIDA_RE.match(digits):
            raise ValueError("NIDA must be exactly 20 digits")
        return digits

    @field_validator("tin")
    @classmethod
    def validate_tin(cls, v: str) -> str:
        digits = "".join(ch for ch in str(v).strip() if ch.isdigit())
        if not _TIN_RE.match(digits):
            raise ValueError("TIN must be exactly 9 digits")
        return digits

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        if v not in ("Male", "Female", "Other"):
            raise ValueError("gender must be Male, Female, or Other")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: str) -> str:
        try:
            dob = date.fromisoformat(v)
        except ValueError:
            raise ValueError("date_of_birth must be YYYY-MM-DD format")
        if dob >= date.today():
            raise ValueError("date_of_birth must be in the past")
        return v

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, v: str) -> str:
        if not _PIN_RE.match(v):
            raise ValueError("PIN must be exactly 4 digits")
        return v


class LenderCreateRequest(BaseModel):
    membership_number: str = Field(min_length=3, max_length=20)
    full_name: str = Field(min_length=2, max_length=200)
    gender: str
    organization: str = Field(min_length=2, max_length=100)
    work_email: str = Field(min_length=5, max_length=254)
    phone: str | None = Field(default=None, max_length=20)
    pin: str

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        if v not in ("Male", "Female", "Other"):
            raise ValueError("gender must be Male, Female, or Other")
        return v

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, v: str) -> str:
        if not _PIN_RE.match(v):
            raise ValueError("PIN must be exactly 4 digits")
        return v


class SubAdminCreateRequest(BaseModel):
    login_id: str = Field(min_length=3, max_length=20)
    full_name: str = Field(min_length=2, max_length=200)
    gender: str
    organization: str = Field(min_length=2, max_length=100)
    work_email: str = Field(min_length=5, max_length=254)
    pin: str

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        if v not in ("Male", "Female", "Other"):
            raise ValueError("gender must be Male, Female, or Other")
        return v

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, v: str) -> str:
        if not _PIN_RE.match(v):
            raise ValueError("PIN must be exactly 4 digits")
        return v


class LoginRequest(BaseModel):
    login_id: str = Field(min_length=3, max_length=20)
    pin: str

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, v: str) -> str:
        if not _PIN_RE.match(v):
            raise ValueError("PIN must be exactly 4 digits")
        return v


class UserResponse(BaseModel):
    id: int
    login_id: str
    full_name: str
    role: str
    gender: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str
    user: UserResponse


class SMEProfileResponse(BaseModel):
    id: int
    nida: str
    phone: str
    email: str | None
    location: str
    business_type: str
    nationality: str
    date_of_birth: date
    tin: str | None = None
    display_token: str
    full_name: str
    gender: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LenderProfileResponse(BaseModel):
    membership_number: str
    full_name: str
    gender: str
    organization: str
    work_email: str
    phone: str | None
    login_id: str | None = None

    model_config = {"from_attributes": True}


class ChangePinRequest(BaseModel):
    current_pin: str
    new_pin: str

    @field_validator("current_pin", "new_pin")
    @classmethod
    def validate_pin(cls, v: str) -> str:
        if not _PIN_RE.match(v):
            raise ValueError("PIN must be exactly 4 digits")
        return v


class ForgotPinRequest(BaseModel):
    """Reset PIN by verifying the date of birth given at registration."""

    login_id: str = Field(min_length=3, max_length=20)
    date_of_birth: str
    new_pin: str

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: str) -> str:
        try:
            dob = date.fromisoformat(v)
        except ValueError:
            raise ValueError("date_of_birth must be YYYY-MM-DD format")
        if dob >= date.today():
            raise ValueError("date_of_birth must be in the past")
        return v

    @field_validator("new_pin")
    @classmethod
    def validate_pin(cls, v: str) -> str:
        if not _PIN_RE.match(v):
            raise ValueError("PIN must be exactly 4 digits")
        return v


class SMEProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    phone: str | None = Field(default=None, min_length=10, max_length=20)
    email: str | None = Field(default=None, max_length=254)
    location: str | None = Field(default=None, min_length=2, max_length=200)
    business_type: str | None = Field(default=None, min_length=2, max_length=100)
    gender: str | None = None
    nationality: str | None = Field(default=None, max_length=50)

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str | None) -> str | None:
        if v is not None and v not in ("Male", "Female", "Other"):
            raise ValueError("gender must be Male, Female, or Other")
        return v


class LenderProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    gender: str | None = None
    organization: str | None = Field(default=None, min_length=2, max_length=100)
    work_email: str | None = Field(default=None, min_length=5, max_length=254)
    phone: str | None = Field(default=None, max_length=20)

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str | None) -> str | None:
        if v is not None and v not in ("Male", "Female", "Other"):
            raise ValueError("gender must be Male, Female, or Other")
        return v


class AdminSelfUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    gender: str | None = None

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str | None) -> str | None:
        if v is not None and v not in ("Male", "Female", "Other"):
            raise ValueError("gender must be Male, Female, or Other")
        return v
