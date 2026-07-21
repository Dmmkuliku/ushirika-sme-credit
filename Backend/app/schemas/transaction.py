"""Transaction request/response schemas (simplified recording fields)."""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"
    OVERDUE = "overdue"
    DEFAULTED = "defaulted"


class TransactionCreate(BaseModel):
    """Crucial fields only — SME TIN comes from the profile automatically."""

    transaction_ref: str = Field(min_length=3, max_length=64)
    counterparty_tin: str = Field(min_length=9, max_length=9, description="Other party TIN — exactly 9 digits")
    counterparty_name: str = Field(min_length=2, max_length=200)
    counterparty_type: str = Field(min_length=2, max_length=50, description="buyer or seller")
    order_type: str = Field(default="sale", min_length=2, max_length=50)
    amount_tzs: float = Field(gt=0)
    currency: str = Field(default="TZS", max_length=10)
    payment_status: PaymentStatus
    transaction_date: datetime
    notes: str | None = None
    due_date: datetime | None = None
    paid_date: datetime | None = None
    days_delayed: int = Field(default=0, ge=0)
    compliance_flag: bool = True
    default_flag: bool = False
    completion_rate: float = Field(default=1.0, ge=0, le=1)

    @field_validator("counterparty_tin")
    @classmethod
    def validate_tin(cls, v: str) -> str:
        digits = "".join(ch for ch in str(v).strip() if ch.isdigit())
        if len(digits) != 9:
            raise ValueError("TIN must be exactly 9 digits")
        return digits

    @field_validator("transaction_date")
    @classmethod
    def validate_transaction_date(cls, v: datetime) -> datetime:
        now = datetime.now(timezone.utc)
        comparable = v if v.tzinfo else v.replace(tzinfo=timezone.utc)
        if comparable > now:
            raise ValueError("Transaction date cannot be in the future")
        return v


class TransactionUpdate(BaseModel):
    transaction_ref: str | None = Field(default=None, min_length=3, max_length=64)
    counterparty_tin: str | None = Field(default=None, min_length=9, max_length=9)
    counterparty_name: str | None = Field(default=None, min_length=2, max_length=200)
    counterparty_type: str | None = Field(default=None, min_length=2, max_length=50)
    order_type: str | None = Field(default=None, min_length=2, max_length=50)
    amount_tzs: float | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, max_length=10)
    payment_status: PaymentStatus | None = None
    transaction_date: datetime | None = None
    notes: str | None = None
    due_date: datetime | None = None
    paid_date: datetime | None = None
    days_delayed: int | None = Field(default=None, ge=0)
    compliance_flag: bool | None = None
    default_flag: bool | None = None
    completion_rate: float | None = Field(default=None, ge=0, le=1)

    @field_validator("counterparty_tin")
    @classmethod
    def validate_tin(cls, v: str | None) -> str | None:
        if v is None:
            return v
        digits = "".join(ch for ch in str(v).strip() if ch.isdigit())
        if len(digits) != 9:
            raise ValueError("TIN must be exactly 9 digits")
        return digits

    @field_validator("transaction_date")
    @classmethod
    def validate_transaction_date(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        now = datetime.now(timezone.utc)
        comparable = v if v.tzinfo else v.replace(tzinfo=timezone.utc)
        if comparable > now:
            raise ValueError("Transaction date cannot be in the future")
        return v


class TransactionResponse(BaseModel):
    id: int
    transaction_ref: str
    counterparty_hash: str
    counterparty_tin: str | None = None
    counterparty_name: str | None = None
    counterparty_type: str
    order_type: str
    amount_tzs: float
    currency: str
    payment_status: PaymentStatus
    due_date: datetime | None = None
    paid_date: datetime | None = None
    days_delayed: int
    compliance_flag: bool
    default_flag: bool
    completion_rate: float
    is_outlier: bool = False
    notes: str | None
    transaction_date: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class CSVImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]
    model_retrained: bool = False
    model_version: str | None = None
    score_ready: bool = False
    score: float | None = None
    risk_band: str | None = None
    eligible_financing_tzs: float | None = None
    probability_creditworthy: float | None = None
    primary_model: str | None = None
    ml_features_display: list[dict] | None = None
    transaction_count: int | None = None
    transactions_needed: int | None = None
    message: str | None = None
    model_training_ran: bool = False
    model_training_scheduled: bool = False
    model_training_version: str | None = None
    model_training_summary: dict | None = None
