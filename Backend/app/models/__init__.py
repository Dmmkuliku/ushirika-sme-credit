import enum
from datetime import datetime, date

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    SME = "sme"
    LENDER = "lender"
    ADMIN = "admin"
    SUBADMIN = "subadmin"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"
    OVERDUE = "overdue"
    DEFAULTED = "defaulted"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    login_id: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    hashed_pin: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sme_profile: Mapped["SMEProfile | None"] = relationship(back_populates="user", uselist=False)
    lender_profile: Mapped["LenderProfile | None"] = relationship(back_populates="user", uselist=False)
    credit_scores: Mapped[list["CreditScore"]] = relationship(back_populates="user")


class SMEProfile(Base):
    __tablename__ = "sme_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    nida: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    nationality: Mapped[str] = mapped_column(String(50), default="Tanzanian", nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    business_type: Mapped[str] = mapped_column(String(100), nullable=False)
    tin: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    display_token: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="sme_profile")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="sme_profile")


class LenderProfile(Base):
    __tablename__ = "lender_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    membership_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    organization: Mapped[str] = mapped_column(String(100), nullable=False)
    work_email: Mapped[str] = mapped_column(String(254), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="lender_profile")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sme_profile_id: Mapped[int] = mapped_column(ForeignKey("sme_profiles.id", ondelete="CASCADE"), index=True)
    transaction_ref: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    counterparty_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    counterparty_tin: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    counterparty_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    counterparty_type: Mapped[str] = mapped_column(String(50), nullable=False)
    order_type: Mapped[str] = mapped_column(String(50), nullable=False)
    amount_tzs: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="TZS", nullable=False)
    payment_status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    days_delayed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    compliance_flag: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    default_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completion_rate: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_outlier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    transaction_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sme_profile: Mapped["SMEProfile"] = relationship(back_populates="transactions")


class CreditScore(Base):
    __tablename__ = "credit_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_band: Mapped[str] = mapped_column(String(20), nullable=False)
    eligible_financing_tzs: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    features_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="credit_scores")


class MonthlyHistory(Base):
    __tablename__ = "monthly_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sme_profile_id: Mapped[int] = mapped_column(ForeignKey("sme_profiles.id", ondelete="CASCADE"), index=True)
    year_month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    total_volume_tzs: Mapped[float] = mapped_column(Float, nullable=False)
    transaction_count: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_delay_days: Mapped[float] = mapped_column(Float, nullable=False)
    on_time_rate: Mapped[float] = mapped_column(Float, nullable=False)
    default_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    compliance_rate: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ModelMetrics(Base):
    __tablename__ = "model_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    accuracy: Mapped[float] = mapped_column(Float, nullable=False)
    precision_score: Mapped[float] = mapped_column(Float, nullable=False)
    recall: Mapped[float] = mapped_column(Float, nullable=False)
    f1: Mapped[float] = mapped_column(Float, nullable=False)
    roc_auc: Mapped[float] = mapped_column(Float, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False)
