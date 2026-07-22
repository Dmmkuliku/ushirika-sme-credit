"""Human-readable labels for ML features — plain language for all users."""

FEATURE_LABELS_EN: dict[str, str] = {
    "payment_consistency": "How reliably they finish payments",
    "payment_delay_avg": "Average late days",
    "payment_delay_max": "Longest late payment (days)",
    "turnover_tzs": "Total money moved (TZS)",
    "transaction_frequency": "How often they trade each month",
    "completion_rate_avg": "How often deals are completed",
    "default_rate": "How often payments fail",
    "compliance_rate": "How often rules are followed",
    "account_age_months": "How long they have been trading (months)",
    "counterparty_diversity": "Number of different trading partners",
    "volume_trend": "Are sales going up or down?",
    "on_time_rate": "Payments made on time",
    "avg_transaction_interval_days": "Days between trades",
    "buyer_share": "Share of sales to customers",
    "supplier_share": "Share of buys from suppliers",
    "distributor_share": "Share of distributor partners",
    "order_type_diversity": "Variety of trade types",
    "outlier_transaction_count": "Very large one-off deals",
    "typical_volume_tzs": "Usual trading amount (TZS)",
}

FEATURE_LABELS_SW: dict[str, str] = {
    "payment_consistency": "Jinsi wanavyomaliza malipo kwa uaminifu",
    "payment_delay_avg": "Wastani wa siku za kuchelewa",
    "payment_delay_max": "Siku nyingi zaidi za kuchelewa",
    "turnover_tzs": "Jumla ya fedha zilizohamishwa (TZS)",
    "transaction_frequency": "Marangapi wanabiashara kwa mwezi",
    "completion_rate_avg": "Marangapi biashara inakamilika",
    "default_rate": "Marangapi malipo yanashindikana",
    "compliance_rate": "Marangapi sheria zinafuatwa",
    "account_age_months": "Muda wa kufanya biashara (miezi)",
    "counterparty_diversity": "Idadi ya washirika tofauti wa biashara",
    "volume_trend": "Mauzo yanaongezeka au yanapungua?",
    "on_time_rate": "Malipo yanayofanywa kwa wakati",
    "avg_transaction_interval_days": "Siku kati ya biashara",
    "buyer_share": "Sehemu ya mauzo kwa wateja",
    "supplier_share": "Sehemu ya ununuzi kutoka wasambazaji",
    "distributor_share": "Sehemu ya wasambazaji wa jumla",
    "order_type_diversity": "Aina mbalimbali za biashara",
    "outlier_transaction_count": "Biashara kubwa za mara moja",
    "typical_volume_tzs": "Kiasi cha kawaida cha biashara (TZS)",
}

# Decision-relevant signals shown to SMEs and lenders (simple wording)
CRUCIAL_DISPLAY_KEYS = [
    "on_time_rate",
    "payment_consistency",
    "default_rate",
    "payment_delay_avg",
    "turnover_tzs",
    "typical_volume_tzs",
    "transaction_frequency",
    "volume_trend",
    "counterparty_diversity",
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
