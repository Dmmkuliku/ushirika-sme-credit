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

    @staticmethod
    def calibrate_probability(raw: float) -> float:
        """
        Map raw classifier probability to an honest display range.

        Tree ensembles can emit exactly 0.0 / 1.0 when every tree agrees — that
        is overconfidence, not certainty. Shrink toward 0.5 and clip to 5%–95%.
        """
        p = max(0.0, min(1.0, float(raw)))
        shrunk = 0.5 + (p - 0.5) * 0.85
        return round(max(0.05, min(0.95, shrunk)), 4)

    def predict_credit_score(self, features: dict[str, float]) -> tuple[float, str]:
        details = self.predict_details(features)
        return details["score"], details["model_version"]

    def predict_details(self, features: dict[str, float]) -> dict[str, Any]:
        """Score + probability for lender/SME explainability."""
        if self.model is None:
            score = self._heuristic_score(features)
            raw_p = max(0.0, min(1.0, (score - 300) / 550))
            return {
                "score": score,
                "model_version": "heuristic-v1",
                "probability_creditworthy": self.calibrate_probability(raw_p),
                "probability_raw": round(raw_p, 4),
                "primary_model": "heuristic",
                "model_loaded": False,
            }

        X = np.array([[features.get(col, 0.0) for col in self.feature_columns]])
        raw_p = float(self.model.predict_proba(X)[0, 1])
        # Map raw probability of good repayment to a clear 300–850 credit score
        score = round(300.0 + max(0.0, min(1.0, raw_p)) * 550.0, 2)
        return {
            "score": score,
            "model_version": self.model_version,
            "probability_creditworthy": self.calibrate_probability(raw_p),
            "probability_raw": round(raw_p, 4),
            "primary_model": "random_forest",
            "model_loaded": True,
        }

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
        return round(300 + max(0, min(1, raw)) * 550, 2)


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
