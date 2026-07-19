"""25% frequency guard for outlier detection."""

from app.services.outliers import amount_outlier_mask, robust_volume_and_caps


def test_rare_large_deal_is_outlier():
    # 9 small + 1 huge → rare spike (< 25%) → outlier
    amounts = [100_000] * 9 + [5_000_000]
    mask = amount_outlier_mask(amounts)
    assert sum(mask) == 1
    assert mask[-1] is True


def test_frequent_large_deals_are_pattern_not_outliers():
    # 7 small + 3 large (30% ≥ 25%) → trading pattern, not outliers
    amounts = [100_000] * 7 + [2_000_000, 2_100_000, 1_900_000]
    mask = amount_outlier_mask(amounts)
    assert mask == [False] * 10


def test_outliers_excluded_from_typical_volume():
    amounts = [50_000] * 9 + [10_000_000]
    caps = robust_volume_and_caps(amounts)
    assert caps["outlier_transaction_count"] == 1
    assert caps["typical_volume_tzs"] == 450_000.0
    assert caps["cap_history_tzs"] == 225_000.0  # 50% of typical
