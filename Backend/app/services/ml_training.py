import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.config import get_settings
from app.services.feature_engineering import FEATURE_COLUMNS


def generate_synthetic_training_data(n_samples: int = 1200, random_seed: int = 42) -> tuple[pd.DataFrame, np.ndarray]:
    rng = np.random.default_rng(random_seed)

    data = {
        "payment_consistency": rng.beta(5, 2, n_samples),
        "payment_delay_avg": rng.gamma(2, 8, n_samples),
        "payment_delay_max": rng.gamma(2, 15, n_samples),
        "turnover_tzs": rng.lognormal(14, 1.2, n_samples),
        "transaction_frequency": rng.gamma(2, 3, n_samples),
        "completion_rate_avg": rng.beta(6, 2, n_samples),
        "default_rate": rng.beta(1.5, 8, n_samples),
        "compliance_rate": rng.beta(8, 2, n_samples),
        "account_age_months": rng.uniform(6, 120, n_samples),
        "counterparty_diversity": rng.beta(3, 3, n_samples),
        "volume_trend": rng.normal(0, 0.3, n_samples),
        "on_time_rate": rng.beta(5, 2, n_samples),
        "avg_transaction_interval_days": rng.gamma(2, 10, n_samples),
    }
    df = pd.DataFrame(data)

    established_good = (
        (df["account_age_months"] >= 42)
        & (df["payment_consistency"] >= 0.72)
        & (df["payment_delay_avg"] <= 16)
        & (df["default_rate"] <= 0.18)
        & (df["avg_transaction_interval_days"] <= 35)
    )
    emerging_good = (
        (df["account_age_months"] < 42)
        & (df["counterparty_diversity"] >= 0.48)
        & (df["volume_trend"] >= -0.02)
        & (df["completion_rate_avg"] >= 0.72)
        & (df["avg_transaction_interval_days"] <= 30)
    )
    resilient_good = (
        (df["compliance_rate"] >= 0.82)
        & (df["on_time_rate"] >= 0.68)
        & (df["payment_delay_max"] <= 35)
        & (df["transaction_frequency"] >= 3.0)
        & (df["avg_transaction_interval_days"] <= 40)
    )
    labels = (established_good | emerging_good | resilient_good).astype(int).to_numpy(copy=True)

    flip = rng.random(n_samples) < 0.025
    labels[flip] = 1 - labels[flip]
    return df, labels


def evaluate_model(model, X_test: np.ndarray, y_test: np.ndarray) -> dict[str, float]:
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    return {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision_score": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, y_proba)),
    }


def train_models(db_session=None) -> dict[str, Any]:
    settings = get_settings()
    os.makedirs(settings.model_dir, exist_ok=True)

    df, labels = generate_synthetic_training_data(random_seed=settings.random_seed)
    X = df[FEATURE_COLUMNS].values
    y = labels

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=settings.random_seed, stratify=y
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=settings.random_seed)

    lr_pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=2000, random_state=settings.random_seed)),
        ]
    )
    lr_grid = GridSearchCV(
        lr_pipeline,
        {"clf__C": [0.01, 0.1, 1.0, 10.0]},
        cv=cv,
        scoring="roc_auc",
        n_jobs=-1,
    )
    lr_grid.fit(X_train, y_train)
    lr_model = lr_grid.best_estimator_
    lr_metrics = evaluate_model(lr_model, X_test, y_test)

    rf_grid = GridSearchCV(
        RandomForestClassifier(random_state=settings.random_seed, n_jobs=-1),
        {
            "n_estimators": [100, 200],
            "max_depth": [6, 10, None],
            "min_samples_leaf": [1, 3, 5],
        },
        cv=cv,
        scoring="roc_auc",
        n_jobs=-1,
    )
    rf_grid.fit(X_train, y_train)
    rf_model = rf_grid.best_estimator_
    rf_metrics = evaluate_model(rf_model, X_test, y_test)

    version = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    rf_path = Path(settings.model_dir) / f"random_forest_{version}.joblib"
    lr_path = Path(settings.model_dir) / f"logistic_regression_{version}.joblib"
    meta_path = Path(settings.model_dir) / "model_meta.json"

    joblib.dump(rf_model, rf_path)
    joblib.dump(lr_model, lr_path)

    rf_outperforms = rf_metrics["roc_auc"] >= lr_metrics["roc_auc"]

    meta = {
        "version": version,
        "primary_model": "random_forest",
        "random_forest_path": str(rf_path),
        "logistic_regression_path": str(lr_path),
        "feature_columns": FEATURE_COLUMNS,
        "rf_metrics": rf_metrics,
        "lr_metrics": lr_metrics,
        "rf_outperforms_baseline": rf_outperforms,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    results = {
        "version": version,
        "rf_metrics": {**rf_metrics, "model_name": "random_forest", "is_primary": True},
        "lr_metrics": {**lr_metrics, "model_name": "logistic_regression", "is_primary": False},
        "rf_outperforms_baseline": rf_outperforms,
    }

    if db_session is not None:
        from app.models import ModelMetrics

        for m in [results["rf_metrics"], results["lr_metrics"]]:
            db_session.add(
                ModelMetrics(
                    model_name=m["model_name"],
                    model_version=version,
                    accuracy=m["accuracy"],
                    precision_score=m["precision_score"],
                    recall=m["recall"],
                    f1=m["f1"],
                    roc_auc=m["roc_auc"],
                    is_primary=m["is_primary"],
                    metrics_json=json.dumps(m),
                )
            )
        db_session.commit()

    return results
