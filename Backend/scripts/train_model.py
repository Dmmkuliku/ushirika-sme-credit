"""Reproducible model training script."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.services.ml_training import train_models


def main():
    settings = get_settings()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        results = train_models(db_session=db)
    finally:
        db.close()

    print("=" * 60)
    print("SME Credit Risk Model Training Report")
    print("=" * 60)
    print(f"Version: {results['version']}")
    print(f"Random seed: {settings.random_seed}")
    print()
    for key, label in [("rf_metrics", "Random Forest (primary)"), ("lr_metrics", "Logistic Regression (baseline)")]:
        m = results[key]
        print(f"{label}:")
        print(f"  Accuracy:  {m['accuracy']:.4f}")
        print(f"  Precision: {m['precision_score']:.4f}")
        print(f"  Recall:    {m['recall']:.4f}")
        print(f"  F1:        {m['f1']:.4f}")
        print(f"  ROC-AUC:   {m['roc_auc']:.4f}")
        print()
    print(f"RF outperforms baseline: {results['rf_outperforms_baseline']}")
    print("=" * 60)

    report_path = Path("TECHNICAL_PERFORMANCE_REPORT.md")
    if report_path.exists():
        print(f"See {report_path} for full technical report.")


if __name__ == "__main__":
    main()
