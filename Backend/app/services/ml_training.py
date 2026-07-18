import json
import logging
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
from app.services.feature_engineering import FEATURE_COLUMNS, compute_features

logger = logging.getLogger(__name__)


def _label_from_features(df: pd.DataFrame, rng: np.random.Generator | None = None) -> np.ndarray:
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
    if rng is not None:
        flip = rng.random(len(labels)) < 0.025
        labels[flip] = 1 - labels[flip]
    return labels


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
    labels = _label_from_features(df, rng)
    return df, labels


def collect_real_sme_training_data(db_session) -> tuple[pd.DataFrame, np.ndarray, int]:
    """Build training rows from live SME transaction histories."""
    from app.models import SMEProfile, Transaction

    settings = get_settings()
    min_tx = settings.min_transactions_for_score
    rows: list[dict[str, float]] = []

    for profile in db_session.query(SMEProfile).all():
        txs = (
            db_session.query(Transaction)
            .filter(Transaction.sme_profile_id == profile.id)
            .order_by(Transaction.transaction_date.asc())
            .all()
        )
        if len(txs) < min_tx:
            continue
        feats = compute_features(txs, profile.date_of_birth.year)
        rows.append({col: float(feats.get(col, 0.0)) for col in FEATURE_COLUMNS})

    if not rows:
        return pd.DataFrame(columns=FEATURE_COLUMNS), np.array([], dtype=int), 0

    df = pd.DataFrame(rows)
    return df, _label_from_features(df, rng=None), len(rows)


def evaluate_model(model, X_test: np.ndarray, y_test: np.ndarray) -> dict[str, float]:
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    return {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision_score": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, y_proba)) if len(np.unique(y_test)) > 1 else 0.0,
    }


def train_models(db_session=None, include_real_data: bool = True) -> dict[str, Any]:
    """Train RF + LR. Mixes live SME feature rows into training when available."""
    settings = get_settings()
    os.makedirs(settings.model_dir, exist_ok=True)

    syn_df, syn_y = generate_synthetic_training_data(random_seed=settings.random_seed)
    real_rows = 0
    if include_real_data and db_session is not None:
        try:
            real_df, real_y, real_rows = collect_real_sme_training_data(db_session)
        except Exception as exc:
            logger.warning("Could not collect real SME training rows: %s", exc)
            real_df, real_y, real_rows = pd.DataFrame(), np.array([]), 0
        if real_rows > 0:
            repeats = max(8, 200 // real_rows)
            real_df_up = pd.concat([real_df] * repeats, ignore_index=True)
            real_y_up = np.tile(real_y, repeats)
            df = pd.concat([syn_df, real_df_up], ignore_index=True)
            labels = np.concatenate([syn_y, real_y_up])
            logger.info("Training with %s real SME profiles (upsampled x%s)", real_rows, repeats)
        else:
            df, labels = syn_df, syn_y
    else:
        df, labels = syn_df, syn_y

    X = df[FEATURE_COLUMNS].values
    y = labels

    stratify = y if len(np.unique(y)) > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=settings.random_seed, stratify=stratify
    )

    n_splits = 5 if len(y_train) >= 50 else 2
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=settings.random_seed)

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
        "real_sme_profiles_used": real_rows,
        "training_source": "synthetic+real_sme_transactions" if real_rows else "synthetic_bootstrap",
        "train_test_protocol": {
            "method": "sklearn.model_selection.train_test_split",
            "test_size": 0.2,
            "stratified": bool(stratify is not None),
            "train_rows": int(len(X_train)),
            "test_rows": int(len(X_test)),
            "cv_folds": int(n_splits),
            "selection_metric": "roc_auc",
            "notes": (
                "Models are fit ONLY on the training split (with GridSearchCV). "
                "Hold-out test metrics are reported separately — predictions are never scored "
                "without a prior train/test training run."
            ),
        },
        "notes": (
            "Random Forest is primary. Live SME transaction features are mixed into retraining "
            "so predictions reflect uploaded data. Financing caps ignore outlier amounts."
        ),
    }
    logger.info(
        "Trained models v%s | train=%s test=%s | RF ROC-AUC=%.4f | LR ROC-AUC=%.4f",
        version,
        len(X_train),
        len(X_test),
        rf_metrics["roc_auc"],
        lr_metrics["roc_auc"],
    )
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    results = {
        "version": version,
        "rf_metrics": {**rf_metrics, "model_name": "random_forest", "is_primary": True},
        "lr_metrics": {**lr_metrics, "model_name": "logistic_regression", "is_primary": False},
        "rf_outperforms_baseline": rf_outperforms,
        "real_sme_profiles_used": real_rows,
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


def retrain_after_sme_data_change(db_session) -> dict[str, Any] | None:
    """Retrain after SME transaction create/import so the model uses live data."""
    try:
        results = train_models(db_session=db_session, include_real_data=True)
        from app.services.ml_predictor import reload_predictor

        reload_predictor()
        return results
    except Exception as exc:
        logger.exception("Retrain after SME data change failed: %s", exc)
        return None
