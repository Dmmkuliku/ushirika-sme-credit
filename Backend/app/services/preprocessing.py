"""
Data preprocessing for SME credit modelling (proposal §3.7).

- Missing values: median imputation (per column)
- Outliers: IQR clipping on continuous features before scaling
- Scaling: StandardScaler or MinMaxScaler (used in model pipelines)
"""
from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from app.services.feature_engineering import FEATURE_COLUMNS

ScalerKind = Literal["standard", "minmax"]


def impute_missing(df: pd.DataFrame, strategy: str = "median") -> tuple[pd.DataFrame, SimpleImputer]:
    """Replace NaN/inf with column medians (or means). Returns cleaned frame + fitted imputer."""
    work = df[FEATURE_COLUMNS].copy()
    work = work.replace([np.inf, -np.inf], np.nan)
    imputer = SimpleImputer(strategy=strategy)
    values = imputer.fit_transform(work)
    cleaned = pd.DataFrame(values, columns=FEATURE_COLUMNS, index=work.index)
    return cleaned, imputer


def clip_feature_outliers(df: pd.DataFrame, cols: list[str] | None = None) -> pd.DataFrame:
    """IQR-based clipping to isolate anomalous spikes without dropping rows."""
    work = df.copy()
    targets = cols or [
        "payment_delay_avg",
        "payment_delay_max",
        "turnover_tzs",
        "transaction_frequency",
        "avg_transaction_interval_days",
    ]
    for col in targets:
        if col not in work.columns:
            continue
        series = work[col].astype(float)
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr <= 0:
            continue
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        work[col] = series.clip(lo, hi)
    return work


def make_scaler(kind: ScalerKind = "standard"):
    if kind == "minmax":
        return MinMaxScaler()
    return StandardScaler()


def preprocess_feature_matrix(
    df: pd.DataFrame,
    *,
    impute_strategy: str = "median",
    clip_outliers: bool = True,
) -> pd.DataFrame:
    """Full scrub used before train/test split: impute → optional IQR clip."""
    cleaned, _ = impute_missing(df, strategy=impute_strategy)
    if clip_outliers:
        cleaned = clip_feature_outliers(cleaned)
    return cleaned
