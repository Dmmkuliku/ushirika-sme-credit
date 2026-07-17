from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from app.models import PaymentStatus, Transaction


def _months_between(start: datetime, end: datetime) -> float:
    return max(1.0, (end.year - start.year) * 12 + (end.month - start.month) + 1)


def compute_features(transactions: list[Transaction], registration_year: int) -> dict[str, float]:
    if not transactions:
        return _empty_features()

    df = pd.DataFrame(
        [
            {
                "amount_tzs": t.amount_tzs,
                "payment_status": t.payment_status.value,
                "days_delayed": t.days_delayed,
                "compliance_flag": t.compliance_flag,
                "default_flag": t.default_flag,
                "completion_rate": t.completion_rate,
                "counterparty_hash": t.counterparty_hash,
                "transaction_date": pd.to_datetime(t.transaction_date),
                "on_time": t.payment_status in (PaymentStatus.PAID,) and t.days_delayed <= 3,
            }
            for t in transactions
        ]
    )

    now = datetime.now(timezone.utc)
    account_age_months = max(1.0, (now.year - registration_year) * 12)

    paid_mask = df["payment_status"].isin(["paid", "partial"])
    payment_consistency = float(df.loc[paid_mask, "completion_rate"].mean()) if paid_mask.any() else 0.0

    payment_delay_avg = float(df["days_delayed"].mean())
    payment_delay_max = float(df["days_delayed"].max())

    turnover_tzs = float(df["amount_tzs"].sum())
    date_span_months = _months_between(
        df["transaction_date"].min().to_pydatetime(),
        df["transaction_date"].max().to_pydatetime(),
    )
    transaction_frequency = float(len(df) / date_span_months)

    completion_rate_avg = float(df["completion_rate"].mean())
    default_rate = float(df["default_flag"].mean())
    compliance_rate = float(df["compliance_flag"].mean())
    on_time_rate = float(df["on_time"].mean())

    counterparty_diversity = float(df["counterparty_hash"].nunique() / max(len(df), 1))

    monthly = df.groupby(df["transaction_date"].dt.to_period("M"))["amount_tzs"].sum()
    if len(monthly) >= 2:
        x = np.arange(len(monthly))
        slope = np.polyfit(x, monthly.values, 1)[0]
        volume_trend = float(slope / (monthly.mean() + 1e-6))
    else:
        volume_trend = 0.0

    sorted_dates = df["transaction_date"].sort_values()
    if len(sorted_dates) >= 2:
        intervals = sorted_dates.diff().dropna().dt.total_seconds() / 86400.0
        avg_transaction_interval_days = float(intervals.mean())
    else:
        avg_transaction_interval_days = 0.0

    return {
        "payment_consistency": round(payment_consistency, 4),
        "payment_delay_avg": round(payment_delay_avg, 4),
        "payment_delay_max": round(payment_delay_max, 4),
        "turnover_tzs": round(turnover_tzs, 2),
        "transaction_frequency": round(transaction_frequency, 4),
        "completion_rate_avg": round(completion_rate_avg, 4),
        "default_rate": round(default_rate, 4),
        "compliance_rate": round(compliance_rate, 4),
        "account_age_months": round(account_age_months, 2),
        "counterparty_diversity": round(counterparty_diversity, 4),
        "volume_trend": round(volume_trend, 4),
        "on_time_rate": round(on_time_rate, 4),
        "avg_transaction_interval_days": round(avg_transaction_interval_days, 4),
    }


def _empty_features() -> dict[str, float]:
    return {
        "payment_consistency": 0.0,
        "payment_delay_avg": 0.0,
        "payment_delay_max": 0.0,
        "turnover_tzs": 0.0,
        "transaction_frequency": 0.0,
        "completion_rate_avg": 0.0,
        "default_rate": 0.0,
        "compliance_rate": 0.0,
        "account_age_months": 1.0,
        "counterparty_diversity": 0.0,
        "volume_trend": 0.0,
        "on_time_rate": 0.0,
        "avg_transaction_interval_days": 0.0,
    }


FEATURE_COLUMNS = [
    "payment_consistency",
    "payment_delay_avg",
    "payment_delay_max",
    "turnover_tzs",
    "transaction_frequency",
    "completion_rate_avg",
    "default_rate",
    "compliance_rate",
    "account_age_months",
    "counterparty_diversity",
    "volume_trend",
    "on_time_rate",
    "avg_transaction_interval_days",
]
