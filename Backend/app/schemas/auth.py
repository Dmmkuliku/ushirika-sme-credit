import re
from datetime import datetime, date

from pydantic import BaseModel, Field, field_validator, model_validator


_PIN_RE = re.compile(r"^\d{4}$")
_NIDA_RE = re.compile(r"^\d{20}$")
_TIN_RE = re.compile(r"^\d{9}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_TZ_PHONE_RE = re.compile(r"^\+255[67]\d{8}$")

TANZANIA_REGIONS = {
    "Arusha",
    "Dar es Salaam",
    "Dodoma",
    "Geita",
    "Iringa",
    "Kagera",
    "Katavi",
    "Kigoma",
    "Kilimanjaro",
    "Lindi",
    "Manyara",
    "Mara",
    "Mbeya",
    "Morogoro",
    "Mtwara",
    "Mwanza",
    "Njombe",
    "Pwani",
    "Rukwa",
    "Ruvuma",
    "Shinyanga",
    "Simiyu",
    "Singida",
    "Songwe",
    "Tabora",
    "Tanga",
    "Kaskazini Unguja",
    "Kusini Unguja",
    "Mjini Magharibi",
    "Kaskazini Pemba",
    "Kusini Pemba",
}


def _require_tanzania_region(v: str | None) -> str | None:
    if v is None:
        return None
    cleaned = str(v).strip()
    if cleaned not in TANZANIA_REGIONS:
        raise ValueError("location must be a Tanzania region")
    return cleaned


def _require_valid_dob(v: str) -> str:
    try:
        date.fromisoformat(v)
    except ValueError:
        raise ValueError("date_of_birth must be YYYY-MM-DD format")
    return v


def _normalize_tz_phone(v: str | None) -> str | None:
    if v is None or not str(v).strip():
        return None
    raw = re.sub(r"[\s()-]", "", str(v).strip())
    if raw.startswith("0"):
        raw = "+255" + raw[1:]
    elif raw.startswith("255"):
        raw = "+" + raw
    elif re.fullmatch(r"[67]\d{8}", raw):
        raw = "+255" + raw
    if not _TZ_PHONE_RE.fullmatch(raw):
        raise ValueError("Phone must contain 9 digits after +255 and start with 6 or 7")
    return raw


def _require_valid_email(v: str | None) -> str | None:
    if v is None:
        return None
    cleaned = str(v).strip()
    if not cleaned:
        return None
    if "@" not in cleaned or not _EMAIL_RE.match(cleaned):
        raise ValueError("Email must include @ and look like a valid address (e.g. name@example.com)")
    return cleaned.lower()


class SMERegisterRequest(BaseModel):
    nida: str = Field(min_length=20, max_length=20, description="Exactly 20 digits")
    phone: str = Field(min_length=9, max_length=20)
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
        value = str(v).strip()
        if not _NIDA_RE.fullmatch(value):
            raise ValueError("NIDA must be exactly 20 digits")
        return value

    @field_validator("tin")
    @classmethod
    def validate_tin(cls, v: str) -> str:
        digits = "".join(ch for ch in str(v).strip() if ch.isdigit())
        if not _TIN_RE.match(digits):
            raise ValueError("TIN must be exactly 9 digits")
        return digits

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        return _require_valid_email(v)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return _normalize_tz_phone(v) or ""

    @field_validator("location")
    @classmethod
    def validate_location(cls, v: str) -> str:
        return _require_tanzania_region(v) or ""

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        if v not in ("Male", "Female"):
            raise ValueError("gender must be Male or Female")
        return v

    @field_validator("nationality")
    @classmethod
    def validate_nationality(cls, v: str) -> str:
        if str(v).strip().lower() != "tanzanian":
            raise ValueError("Only Tanzanian SMEs can register")
        return "Tanzanian"

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: str) -> str:
        return _require_valid_dob(v)

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, v: str) -> str:
        if not _PIN_RE.match(v):
            raise ValueError("PIN must be exactly 4 digits")
        return v

    @model_validator(mode="after")
    def validate_dob_matches_nida(self):
        dob = date.fromisoformat(self.date_of_birth)
        if self.nida[:8] != dob.strftime("%Y%m%d"):
            raise ValueError(
                "Date of birth must match the first 8 NIDA digits (YYYYMMDD)"
            )
        return self


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
        if v not in ("Male", "Female"):
            raise ValueError("gender must be Male or Female")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        return _normalize_tz_phone(v)

    @field_validator("work_email")
    @classmethod
    def validate_work_email(cls, v: str) -> str:
        cleaned = _require_valid_email(v)
        if cleaned is None:
            raise ValueError("Email must include @ and look like a valid address (e.g. name@example.com)")
        return cleaned

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
        if v not in ("Male", "Female"):
            raise ValueError("gender must be Male or Female")
        return v

    @field_validator("work_email")
    @classmethod
    def validate_work_email(cls, v: str) -> str:
        cleaned = _require_valid_email(v)
        if cleaned is None:
            raise ValueError("Email must include @ and look like a valid address (e.g. name@example.com)")
        return cleaned

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
    """Reset PIN by verifying the date of birth and registered phone number."""

    login_id: str = Field(min_length=3, max_length=20)
    date_of_birth: str
    phone: str = Field(min_length=9, max_length=20)
    new_pin: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return _normalize_tz_phone(v) or ""

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
    phone: str | None = Field(default=None, min_length=9, max_length=20)
    email: str | None = Field(default=None, max_length=254)
    location: str | None = Field(default=None, min_length=2, max_length=200)
    business_type: str | None = Field(default=None, min_length=2, max_length=100)
    gender: str | None = None

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

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        return _require_valid_email(v)


class LenderProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    gender: str | None = None
    organization: str | None = Field(default=None, min_length=2, max_length=100)
    work_email: str | None = Field(default=None, min_length=5, max_length=254)
    phone: str | None = Field(default=None, max_length=20)

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

    @field_validator("work_email")
    @classmethod
    def validate_work_email(cls, v: str | None) -> str | None:
        return _require_valid_email(v)


class AdminSelfUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    gender: str | None = None

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str | None) -> str | None:
        if v is not None and v not in ("Male", "Female"):
            raise ValueError("gender must be Male or Female")
        return v
