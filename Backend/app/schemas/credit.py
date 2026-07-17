from datetime import datetime

from pydantic import BaseModel


class FeatureVector(BaseModel):
    payment_consistency: float
    payment_delay_avg: float
    payment_delay_max: float
    turnover_tzs: float
    transaction_frequency: float
    completion_rate_avg: float
    default_rate: float
    compliance_rate: float
    account_age_months: float
    counterparty_diversity: float
    volume_trend: float
    on_time_rate: float
    avg_transaction_interval_days: float = 0.0


class CreditScoreResponse(BaseModel):
    id: int
    score: float
    risk_band: str
    eligible_financing_tzs: float
    model_version: str
    features: FeatureVector
    created_at: datetime
    transaction_count: int
    eligible: bool

    model_config = {"from_attributes": True}


class CreditScoreRequest(BaseModel):
    force_refresh: bool = False


class ModelMetricsResponse(BaseModel):
    model_name: str
    model_version: str
    accuracy: float
    precision_score: float
    recall: float
    f1: float
    roc_auc: float
    is_primary: bool
    trained_at: datetime

    model_config = {"from_attributes": True}


class TrainingResultResponse(BaseModel):
    primary_model: str
    models: list[ModelMetricsResponse]
    rf_outperforms_baseline: bool
    message: str
