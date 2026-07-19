"""Outlier detection for transaction amounts (25% pattern rule).

A deal is treated as an outlier only when it is unusually large AND such large
deals are rare (fewer than 25% of all recorded transactions).

If at least 25% of transactions are similarly large (e.g. 3 of 10), that is a
trading pattern — those deals are NOT outliers and may support financing.
Outlier amounts are excluded when estimating loan size.
"""

from __future__ import annotations

from statistics import median
from typing import Sequence


def amount_outlier_mask(amounts: Sequence[float]) -> list[bool]:
    """
    High-side outliers with a 25% frequency guard.

    Steps:
    1. Find candidate large amounts (IQR upper fence, or > 2× median).
    2. If candidates make up ≥ 25% of all txs → pattern, not outliers.
    3. If candidates are < 25% → mark those rare large deals as outliers.
    """
    values = [float(a) for a in amounts]
    n = len(values)
    if n < 4:
        return [False] * n

    ordered = sorted(values)
    q1 = _percentile(ordered, 25)
    q3 = _percentile(ordered, 75)
    iqr = q3 - q1
    med = median(values) or 1.0

    if iqr > 0:
        upper = q3 + 1.5 * iqr
        candidates = [v > upper for v in values]
    else:
        candidates = [v > med * 2.0 for v in values]

    candidate_count = sum(1 for c in candidates if c)
    # ≥ 25% of deals are "large" → normal pattern for this SME
    if candidate_count / n >= 0.25:
        return [False] * n

    return candidates


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
    """Lending caps from typical (non-outlier) volume only — keeps offers realistic."""
    values = [float(a) for a in amounts if a is not None]
    mask = amount_outlier_mask(values)
    typical = [v for v, is_out in zip(values, mask) if not is_out]
    outliers = [v for v, is_out in zip(values, mask) if is_out]

    if not typical:
        typical = values[:]

    total_all = sum(values) if values else 0.0
    typical_volume = sum(typical)
    med = median(typical) if typical else 0.0
    # Conservative: ~4–6 typical deals, or 50% of non-outlier history
    cap_experience = med * 6 if med > 0 else 0.0
    cap_history = typical_volume * 0.50
    return {
        "total_volume_tzs": round(total_all, 2),
        "typical_volume_tzs": round(typical_volume, 2),
        "outlier_transaction_count": len(outliers),
        "median_typical_amount_tzs": round(med, 2),
        "cap_experience_tzs": round(cap_experience, 2),
        "cap_history_tzs": round(cap_history, 2),
    }
