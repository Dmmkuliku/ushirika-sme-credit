import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from app.config import get_settings
from app.services.feature_engineering import FEATURE_COLUMNS


class CreditPredictor:
    def __init__(self) -> None:
        self.model = None
        self.model_version = "untrained"
        self.feature_columns = FEATURE_COLUMNS
        self._load_model()

    def _load_model(self) -> None:
        settings = get_settings()
        meta_path = Path(settings.model_dir) / "model_meta.json"
        if not meta_path.exists():
            return
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        rf_path = Path(meta["random_forest_path"])
        if rf_path.exists():
            self.model = joblib.load(rf_path)
            self.model_version = meta.get("version", "unknown")
            self.feature_columns = meta.get("feature_columns", FEATURE_COLUMNS)

    @property
    def is_loaded(self) -> bool:
        return self.model is not None

    def predict_credit_score(self, features: dict[str, float]) -> tuple[float, str]:
        if self.model is None:
            return self._heuristic_score(features), "heuristic-v1"

        X = np.array([[features.get(col, 0.0) for col in self.feature_columns]])
        proba = float(self.model.predict_proba(X)[0, 1])
        # Conservative mapping: dampen extremes toward a moderate 350–680 band.
        raw = 300 + proba * 500
        score = 350 + (raw - 350) * 0.66
        return round(max(300.0, min(680.0, score)), 2), self.model_version

    def _heuristic_score(self, features: dict[str, float]) -> float:
        raw = (
            0.25 * features.get("payment_consistency", 0)
            + 0.18 * features.get("on_time_rate", 0)
            + 0.12 * features.get("compliance_rate", 0)
            + 0.10 * features.get("completion_rate_avg", 0)
            + 0.10 * features.get("counterparty_diversity", 0)
            - 0.10 * min(features.get("default_rate", 0) * 2, 1)
            - 0.05 * min(features.get("payment_delay_avg", 0) / 60, 1)
            - 0.05 * min(features.get("avg_transaction_interval_days", 0) / 90, 1)
        )
        return round(300 + max(0, min(1, raw)) * 500, 2)


_predictor: CreditPredictor | None = None


def get_predictor() -> CreditPredictor:
    global _predictor
    if _predictor is None:
        _predictor = CreditPredictor()
    return _predictor


def reload_predictor() -> CreditPredictor:
    global _predictor
    _predictor = CreditPredictor()
    return _predictor
