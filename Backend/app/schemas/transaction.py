"""Transaction request/response schemas (simplified recording fields)."""

from datetime import datetime
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
    counterparty_tin: str = Field(min_length=9, max_length=20, description="TIN of the other party")
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
        cleaned = "".join(ch for ch in v.strip().upper() if ch.isalnum())
        if len(cleaned) < 9:
            raise ValueError("TIN must be at least 9 characters")
        return cleaned


class TransactionUpdate(BaseModel):
    transaction_ref: str | None = Field(default=None, min_length=3, max_length=64)
    counterparty_tin: str | None = Field(default=None, min_length=9, max_length=20)
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
        cleaned = "".join(ch for ch in v.strip().upper() if ch.isalnum())
        if len(cleaned) < 9:
            raise ValueError("TIN must be at least 9 characters")
        return cleaned


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
