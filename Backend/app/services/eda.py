"""
Explatory data analysis for proposal §3.7 (Seaborn + Plotly).

Generates figures under Backend/reports/eda/ and a small HTML summary.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from app.config import get_settings
from app.services.feature_engineering import FEATURE_COLUMNS
from app.services.ml_training import generate_synthetic_training_data
from app.services.preprocessing import preprocess_feature_matrix


def _eda_dir() -> Path:
    settings = get_settings()
    root = Path(settings.model_dir).resolve().parent / "reports" / "eda"
    root.mkdir(parents=True, exist_ok=True)
    return root


def build_analysis_frame(db_session=None) -> tuple[pd.DataFrame, np.ndarray, dict[str, Any]]:
    """Prefer live SME features when available; otherwise synthetic bootstrap."""
    from app.services.ml_training import collect_real_sme_training_data

    meta: dict[str, Any] = {"source": "synthetic_bootstrap", "rows": 0}
    syn_df, syn_y = generate_synthetic_training_data(n_samples=800, random_seed=42)
    df, y = syn_df, syn_y
    meta["rows"] = len(df)

    if db_session is not None:
        try:
            real_df, real_y, real_n = collect_real_sme_training_data(db_session)
            if real_n > 0:
                df = pd.concat([syn_df, real_df], ignore_index=True)
                y = np.concatenate([syn_y, real_y])
                meta = {"source": "synthetic+real_sme", "rows": len(df), "real_sme_profiles": real_n}
        except Exception as exc:
            meta["real_data_error"] = str(exc)

    df = preprocess_feature_matrix(df)
    return df, y, meta


def run_eda(db_session=None) -> dict[str, Any]:
    out = _eda_dir()
    df, y, meta = build_analysis_frame(db_session)
    labels = pd.Series(y, name="creditworthy")

    sns.set_theme(style="whitegrid", context="notebook")

    # 1) Correlation heatmap (Seaborn)
    corr = df[FEATURE_COLUMNS].corr()
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(corr, cmap="RdYlGn", center=0, ax=ax, square=True, cbar_kws={"shrink": 0.7})
    ax.set_title("Feature correlation (preprocessed supply-chain signals)")
    fig.tight_layout()
    corr_path = out / "feature_correlation.png"
    fig.savefig(corr_path, dpi=120)
    plt.close(fig)

    # 2) Target distribution
    fig, ax = plt.subplots(figsize=(6, 4))
    plot_df = pd.DataFrame({"label": labels.map({0: "Higher risk", 1: "Creditworthy"})})
    sns.countplot(data=plot_df, x="label", hue="label", ax=ax, palette=["#8A5A00", "#1A7A6D"], legend=False)
    ax.set_title("Class balance (training labels)")
    ax.set_xlabel("")
    fig.tight_layout()
    bal_path = out / "class_balance.png"
    fig.savefig(bal_path, dpi=120)
    plt.close(fig)

    # 3) Payment behaviour density
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    sns.kdeplot(data=df, x="payment_consistency", fill=True, ax=axes[0], color="#1A7A6D")
    axes[0].set_title("Payment consistency density")
    sns.kdeplot(data=df, x="default_rate", fill=True, ax=axes[1], color="#8A5A00")
    axes[1].set_title("Default rate density")
    fig.tight_layout()
    dens_path = out / "payment_density.png"
    fig.savefig(dens_path, dpi=120)
    plt.close(fig)

    # 4) Plotly interactive scatter (HTML)
    try:
        import plotly.express as px

        plot_df = df.copy()
        plot_df["label"] = labels.map({0: "Higher risk", 1: "Creditworthy"})
        fig_px = px.scatter(
            plot_df,
            x="turnover_tzs",
            y="on_time_rate",
            color="label",
            size="transaction_frequency",
            hover_data=["buyer_share", "supplier_share", "counterparty_diversity"],
            title="Turnover vs on-time rate (value-chain behaviour)",
            color_discrete_sequence=["#8A5A00", "#1A7A6D"],
        )
        plotly_path = out / "turnover_vs_ontime.html"
        fig_px.write_html(str(plotly_path), include_plotlyjs="cdn")
    except Exception as exc:
        plotly_path = None
        meta["plotly_error"] = str(exc)

    summary = {
        "rows": int(len(df)),
        "features": FEATURE_COLUMNS,
        "class_counts": {
            "higher_risk": int((y == 0).sum()),
            "creditworthy": int((y == 1).sum()),
        },
        "feature_means": {c: float(df[c].mean()) for c in FEATURE_COLUMNS},
        "figures": {
            "correlation": str(corr_path),
            "class_balance": str(bal_path),
            "payment_density": str(dens_path),
            "plotly_scatter": str(plotly_path) if plotly_path else None,
        },
        "meta": meta,
    }
    summary_path = out / "eda_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary["summary_path"] = str(summary_path)
    return summary
