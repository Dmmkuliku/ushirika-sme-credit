"""Human-readable labels for ML features shown to non-technical users."""

FEATURE_LABELS_EN: dict[str, str] = {
    "payment_consistency": "Payment reliability",
    "payment_delay_avg": "Average payment delay (days)",
    "payment_delay_max": "Longest payment delay (days)",
    "turnover_tzs": "Total business volume (TZS)",
    "transaction_frequency": "Transactions per month",
    "completion_rate_avg": "Average order completion",
    "default_rate": "Default rate",
    "compliance_rate": "Compliance rate",
    "account_age_months": "Account age (months)",
    "counterparty_diversity": "Business partner diversity",
    "volume_trend": "Sales volume trend",
    "on_time_rate": "On-time payment rate",
    "avg_transaction_interval_days": "Average days between transactions",
    "buyer_share": "Share of buyer counterparties",
    "supplier_share": "Share of supplier counterparties",
    "distributor_share": "Share of distributor counterparties",
    "order_type_diversity": "Order-type diversity (value chain)",
    "outlier_transaction_count": "Unusual large transactions (excluded from loan)",
    "typical_volume_tzs": "Typical volume excluding outliers (TZS)",
}

FEATURE_LABELS_SW: dict[str, str] = {
    "payment_consistency": "Uaminifu wa malipo",
    "payment_delay_avg": "Wastani wa ucheleweshaji wa malipo (siku)",
    "payment_delay_max": "Ucheleweshaji mrefu zaidi wa malipo (siku)",
    "turnover_tzs": "Jumla ya biashara (TZS)",
    "transaction_frequency": "Miamala kwa mwezi",
    "completion_rate_avg": "Wastani wa ukamilishaji wa oda",
    "default_rate": "Kiwango cha kushindwa kulipa",
    "compliance_rate": "Kiwango cha kufuata sheria",
    "account_age_months": "Umri wa akaunti (miezi)",
    "counterparty_diversity": "Utofauti wa washirika wa biashara",
    "volume_trend": "Mwelekeo wa kiasi cha mauzo",
    "on_time_rate": "Kiwango cha malipo kwa wakati",
    "avg_transaction_interval_days": "Wastani wa siku kati ya miamala",
    "buyer_share": "Sehemu ya wanunuzi",
    "supplier_share": "Sehemu ya wasambazaji",
    "distributor_share": "Sehemu ya wasambazaji wa jumla",
    "order_type_diversity": "Utofauti wa aina za oda (mnyororo wa thamani)",
    "outlier_transaction_count": "Miamala mikubwa isiyo ya kawaida (haitumiki kwenye mkopo)",
    "typical_volume_tzs": "Kiasi cha kawaida bila miamala isiyo ya kawaida (TZS)",
}

# Only the most decision-relevant signals shown to SMEs and lenders
CRUCIAL_DISPLAY_KEYS = [
    "payment_consistency",
    "on_time_rate",
    "default_rate",
    "payment_delay_avg",
    "typical_volume_tzs",
    "turnover_tzs",
    "transaction_frequency",
    "volume_trend",
    "compliance_rate",
    "outlier_transaction_count",
]


def label_for(feature_key: str, lang: str = "en") -> str:
    table = FEATURE_LABELS_SW if str(lang).lower().startswith("sw") else FEATURE_LABELS_EN
    return table.get(feature_key, feature_key.replace("_", " ").title())


def humanize_features(features: dict | None, lang: str = "en", crucial_only: bool = True) -> list[dict]:
    if not features:
        return []
    skip = {"outlier_flags"}
    keys = CRUCIAL_DISPLAY_KEYS if crucial_only else list(features.keys())
    items = []
    for key in keys:
        if key in skip or key not in features:
            continue
        value = features[key]
        if isinstance(value, (list, dict)):
            continue
        items.append({"name": label_for(key, lang), "key": key, "value": value})
    return items
