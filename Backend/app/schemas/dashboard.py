from datetime import datetime, date

from pydantic import BaseModel


class SMEProfileResponse(BaseModel):
    id: int
    display_token: str
    business_type: str
    nida: str
    full_name: str
    phone: str
    email: str | None
    location: str
    nationality: str
    date_of_birth: date
    created_at: datetime

    model_config = {"from_attributes": True}


class SMEPortfolioItem(BaseModel):
    sme_profile_id: int
    display_token: str
    business_type: str
    nida: str
    full_name: str
    transaction_count: int
    latest_score: float | None
    risk_band: str | None
    eligible_financing_tzs: float | None
    last_activity: datetime | None


class SMEDetailResponse(BaseModel):
    sme_profile_id: int
    display_token: str
    business_type: str
    nida: str
    full_name: str
    phone: str
    email: str | None
    location: str
    nationality: str
    date_of_birth: date
    transaction_count: int
    total_volume_tzs: float
    latest_score: float | None
    risk_band: str | None
    eligible_financing_tzs: float | None
    monthly_history: list["MonthlyHistoryResponse"]


class MonthlyHistoryResponse(BaseModel):
    year_month: str
    total_volume_tzs: float
    transaction_count: int
    avg_delay_days: float
    on_time_rate: float
    default_count: int
    compliance_rate: float

    model_config = {"from_attributes": True}


class DashboardSummary(BaseModel):
    total_smes: int
    total_transactions: int
    total_volume_tzs: float
    average_score: float | None
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    eligible_financing_total_tzs: float


class SMEDashboardSummary(BaseModel):
    transaction_count: int
    total_volume_tzs: float
    latest_score: float | None
    risk_band: str | None
    eligible_financing_tzs: float | None
    score_eligible: bool
    score_locked: bool
    transactions_needed: int
    score_components: dict[str, float] | None = None
