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
    classification_report,
    confusion_matrix,
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
from app.services.preprocessing import preprocess_feature_matrix

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
    buyer = df["buyer_share"] if "buyer_share" in df.columns else 0
    supplier = df["supplier_share"] if "supplier_share" in df.columns else 0
    order_div = df["order_type_diversity"] if "order_type_diversity" in df.columns else 0
    value_chain_good = (
        (buyer + supplier >= 0.55)
        & (order_div >= 0.08)
        & (df["on_time_rate"] >= 0.62)
        & (df["default_rate"] <= 0.22)
    )
    labels = (established_good | emerging_good | resilient_good | value_chain_good).astype(int).to_numpy(copy=True)
    if rng is not None:
        # Tiny label noise only — keep signal strong for reliable learning
        flip = rng.random(len(labels)) < 0.01
        labels[flip] = 1 - labels[flip]
    return labels


def generate_synthetic_training_data(n_samples: int = 1200, random_seed: int = 42) -> tuple[pd.DataFrame, np.ndarray]:
    rng = np.random.default_rng(random_seed)

    buyer = rng.beta(2, 2, n_samples)
    supplier = rng.beta(2, 2, n_samples)
    distributor = np.clip(1.0 - buyer - supplier, 0.0, 1.0)
    total = buyer + supplier + distributor + 1e-9
    buyer, supplier, distributor = buyer / total, supplier / total, distributor / total

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
        "buyer_share": buyer,
        "supplier_share": supplier,
        "distributor_share": distributor,
        "order_type_diversity": rng.uniform(0.05, 0.45, n_samples),
    }
    df = pd.DataFrame(data)
    # Inject a few NaNs so imputation is exercised (proposal §3.7)
    for col in ("payment_consistency", "turnover_tzs", "buyer_share"):
        idx = rng.choice(n_samples, size=max(1, n_samples // 40), replace=False)
        df.loc[idx, col] = np.nan
    labels = _label_from_features(df.fillna(df.median(numeric_only=True)), rng)
    return df, labels


def collect_real_sme_training_data(db_session) -> tuple[pd.DataFrame, np.ndarray, int]:
    """Build training rows from live SME transaction histories (PII never included)."""
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


def _confusion_payload(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    report = classification_report(
        y_true, y_pred, labels=[0, 1], target_names=["higher_risk", "creditworthy"], output_dict=True, zero_division=0
    )
    return {
        "matrix": cm.tolist(),
        "labels": ["higher_risk (0)", "creditworthy (1)"],
        "tn": int(cm[0, 0]),
        "fp": int(cm[0, 1]),
        "fn": int(cm[1, 0]),
        "tp": int(cm[1, 1]),
        "classification_report": report,
    }


def evaluate_model(model, X_test: np.ndarray, y_test: np.ndarray) -> dict[str, Any]:
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision_score": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, y_proba)) if len(np.unique(y_test)) > 1 else 0.0,
        "confusion_matrix": _confusion_payload(y_test, y_pred),
    }
    return metrics


def _statsmodels_logit_auc(X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray, y_test: np.ndarray) -> dict[str, Any]:
    """Classical statsmodels Logit benchmark (proposal §3.2 tools list)."""
    try:
        import statsmodels.api as sm
    except Exception as exc:
        return {"available": False, "error": str(exc)}

    try:
        scaler = StandardScaler()
        Xt = scaler.fit_transform(X_train)
        Xs = scaler.transform(X_test)
        Xt_c = sm.add_constant(Xt, has_constant="add")
        Xs_c = sm.add_constant(Xs, has_constant="add")
        model = sm.Logit(y_train, Xt_c).fit(disp=False, maxiter=200)
        proba = model.predict(Xs_c)
        pred = (proba >= 0.5).astype(int)
        return {
            "available": True,
            "accuracy": float(accuracy_score(y_test, pred)),
            "roc_auc": float(roc_auc_score(y_test, proba)) if len(np.unique(y_test)) > 1 else 0.0,
            "pseudo_r2": float(getattr(model, "prsquared", 0.0) or 0.0),
        }
    except Exception as exc:
        logger.warning("statsmodels Logit failed: %s", exc)
        return {"available": False, "error": str(exc)}


def train_models(db_session=None, include_real_data: bool = True) -> dict[str, Any]:
    """Train RF + LR with preprocessing, 80/20 split, k-fold CV, and full metrics."""
    settings = get_settings()
    os.makedirs(settings.model_dir, exist_ok=True)
    reports_dir = Path(settings.model_dir).resolve().parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

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

    # §3.7 preprocessing: median imputation + IQR clip (PII never in matrix)
    df = preprocess_feature_matrix(df)
    X = df[FEATURE_COLUMNS].values
    y = labels

    stratify = y if len(np.unique(y)) > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=settings.random_seed, stratify=stratify
    )

    n_splits = 5 if len(y_train) >= 50 else 2
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=settings.random_seed)

    # Classical LR with StandardScaler (proposal feature scaling)
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
        RandomForestClassifier(
            random_state=settings.random_seed,
            n_jobs=-1,
            class_weight="balanced_subsample",
            bootstrap=True,
        ),
        {
            "n_estimators": [200, 400],
            "max_depth": [8, 14, None],
            "min_samples_leaf": [1, 2],
            "min_samples_split": [2, 5],
            "max_features": ["sqrt", 0.6],
        },
        cv=cv,
        scoring="roc_auc",
        n_jobs=-1,
    )
    rf_grid.fit(X_train, y_train)
    rf_model = rf_grid.best_estimator_
    rf_metrics = evaluate_model(rf_model, X_test, y_test)

    sm_metrics = _statsmodels_logit_auc(X_train, y_train, X_test, y_test)

    feature_importance = {}
    if hasattr(rf_model, "feature_importances_"):
        feature_importance = {
            col: float(imp) for col, imp in zip(FEATURE_COLUMNS, rf_model.feature_importances_)
        }

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
        "statsmodels_logit": sm_metrics,
        "feature_importance": feature_importance,
        "rf_outperforms_baseline": rf_outperforms,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "real_sme_profiles_used": real_rows,
        "training_source": "synthetic+real_sme_transactions" if real_rows else "synthetic_bootstrap",
        "preprocessing": {
            "missing_values": "median imputation (SimpleImputer)",
            "outliers": "IQR clip on continuous delay/volume features",
            "scaling": "StandardScaler inside Logistic Regression pipeline",
            "pii_policy": "Feature matrix excludes names, NIDA, phone, email, TIN",
        },
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
                "Hold-out test metrics and confusion matrices are reported separately."
            ),
        },
        "training_recipe": "strong_rf_v2",
        "notes": (
            "Random Forest is primary with balanced class weights and a wider "
            "hyperparameter search. Value-chain role shares and order-type diversity "
            "are included. Live SME features mix into retraining."
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

    # Persist evaluation artifacts for the technical report
    eval_path = reports_dir / "latest_evaluation.json"
    with open(eval_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "version": version,
                "rf_metrics": rf_metrics,
                "lr_metrics": lr_metrics,
                "statsmodels_logit": sm_metrics,
                "feature_importance": feature_importance,
                "rf_outperforms_baseline": rf_outperforms,
            },
            f,
            indent=2,
        )

    results = {
        "version": version,
        "rf_metrics": {**rf_metrics, "model_name": "random_forest", "is_primary": True},
        "lr_metrics": {**lr_metrics, "model_name": "logistic_regression", "is_primary": False},
        "rf_outperforms_baseline": rf_outperforms,
        "real_sme_profiles_used": real_rows,
        "statsmodels_logit": sm_metrics,
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
