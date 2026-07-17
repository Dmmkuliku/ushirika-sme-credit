from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"
    OVERDUE = "overdue"
    DEFAULTED = "defaulted"


class TransactionCreate(BaseModel):
    transaction_ref: str = Field(min_length=3, max_length=64)
    counterparty_name: str = Field(min_length=2, max_length=200)
    counterparty_type: str = Field(min_length=2, max_length=50)
    order_type: str = Field(min_length=2, max_length=50)
    amount_tzs: float = Field(gt=0)
    currency: str = Field(default="TZS", max_length=10)
    payment_status: PaymentStatus
    due_date: datetime
    paid_date: datetime | None = None
    days_delayed: int = Field(default=0, ge=0)
    compliance_flag: bool = True
    default_flag: bool = False
    completion_rate: float = Field(default=1.0, ge=0, le=1)
    notes: str | None = None
    transaction_date: datetime


class TransactionUpdate(BaseModel):
    transaction_ref: str | None = Field(default=None, min_length=3, max_length=64)
    counterparty_name: str | None = Field(default=None, min_length=2, max_length=200)
    counterparty_type: str | None = Field(default=None, min_length=2, max_length=50)
    order_type: str | None = Field(default=None, min_length=2, max_length=50)
    amount_tzs: float | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, max_length=10)
    payment_status: PaymentStatus | None = None
    due_date: datetime | None = None
    paid_date: datetime | None = None
    days_delayed: int | None = Field(default=None, ge=0)
    compliance_flag: bool | None = None
    default_flag: bool | None = None
    completion_rate: float | None = Field(default=None, ge=0, le=1)
    notes: str | None = None
    transaction_date: datetime | None = None


class TransactionResponse(BaseModel):
    id: int
    transaction_ref: str
    counterparty_hash: str
    counterparty_type: str
    order_type: str
    amount_tzs: float
    currency: str
    payment_status: PaymentStatus
    due_date: datetime
    paid_date: datetime | None
    days_delayed: int
    compliance_flag: bool
    default_flag: bool
    completion_rate: float
    notes: str | None
    transaction_date: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class CSVImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]
