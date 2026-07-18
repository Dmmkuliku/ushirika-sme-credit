"""Outlier detection for transaction amounts (IQR method)."""

from __future__ import annotations

from statistics import median
from typing import Sequence


def amount_outlier_mask(amounts: Sequence[float]) -> list[bool]:
    """Return True for amounts that are statistical high-side outliers."""
    values = [float(a) for a in amounts]
    n = len(values)
    if n < 4:
        return [False] * n

    ordered = sorted(values)
    q1 = _percentile(ordered, 25)
    q3 = _percentile(ordered, 75)
    iqr = q3 - q1
    if iqr <= 0:
        # Fall back: flag values > 3x median as outliers when spread is tiny
        med = median(values) or 1.0
        return [v > med * 3.0 for v in values]

    upper = q3 + 1.5 * iqr
    return [v > upper for v in values]


def _percentile(ordered: list[float], pct: float) -> float:
    if not ordered:
        return 0.0
    k = (len(ordered) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(ordered) - 1)
    if f == c:
        return ordered[f]
    return ordered[f] + (ordered[c] - ordered[f]) * (k - f)


def robust_volume_and_caps(amounts: Sequence[float]) -> dict[str, float | int]:
    """Compute lending caps that ignore one-off unusually large deals."""
    values = [float(a) for a in amounts if a is not None]
    mask = amount_outlier_mask(values)
    typical = [v for v, is_out in zip(values, mask) if not is_out]
    outliers = [v for v, is_out in zip(values, mask) if is_out]

    if not typical:
        typical = values[:]

    total_all = sum(values) if values else 0.0
    typical_volume = sum(typical)
    med = median(typical) if typical else 0.0
    # At most about 6–8 typical deals, or 75% of non-outlier history — whichever is smaller.
    cap_experience = med * 8 if med > 0 else 0.0
    cap_history = typical_volume * 0.75
    return {
        "total_volume_tzs": round(total_all, 2),
        "typical_volume_tzs": round(typical_volume, 2),
        "outlier_transaction_count": len(outliers),
        "median_typical_amount_tzs": round(med, 2),
        "cap_experience_tzs": round(cap_experience, 2),
        "cap_history_tzs": round(cap_history, 2),
    }
