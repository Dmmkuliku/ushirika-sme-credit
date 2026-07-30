from app.services.credit_scoring import financing_from_prediction, risk_band_from_score
from app.services.feature_engineering import FEATURE_COLUMNS
from app.services.ml_training import generate_synthetic_training_data, train_models
from app.services.ml_predictor import CreditPredictor
from app.services.preprocessing import preprocess_feature_matrix


def test_synthetic_data_shape():
    df, labels = generate_synthetic_training_data(n_samples=200, random_seed=42)
    assert len(df) == 200
    assert len(labels) == 200
    assert set(labels).issubset({0, 1})
    for col in FEATURE_COLUMNS:
        assert col in df.columns


def test_preprocessing_imputes_nans():
    df, _ = generate_synthetic_training_data(n_samples=100, random_seed=7)
    assert df.isna().any().any()
    cleaned = preprocess_feature_matrix(df)
    assert not cleaned.isna().any().any()
    assert list(cleaned.columns) == FEATURE_COLUMNS


def test_train_models_rf_outperforms():
    results = train_models(db_session=None)
    assert "rf_metrics" in results
    assert "lr_metrics" in results
    assert results["rf_metrics"]["roc_auc"] > 0.5
    assert results["lr_metrics"]["roc_auc"] > 0.5
    assert results["rf_outperforms_baseline"] is True
    assert "confusion_matrix" in results["rf_metrics"]
    assert "matrix" in results["rf_metrics"]["confusion_matrix"]


def test_probability_never_claims_certainty():
    assert CreditPredictor.calibrate_probability(1.0) <= 0.95
    assert CreditPredictor.calibrate_probability(0.0) >= 0.05
    mid = CreditPredictor.calibrate_probability(0.5)
    assert 0.45 <= mid <= 0.55


def test_financing_follows_volume_and_probability():
    amounts = [800_000.0] * 12
    total = sum(amounts)
    low, _ = financing_from_prediction(
        420,
        0.25,
        amounts,
        {
            "on_time_rate": 0.4,
            "payment_consistency": 0.4,
            "default_rate": 0.3,
            "volume_trend": 0.0,
            "transaction_frequency": 2.0,
            "compliance_rate": 0.5,
        },
    )
    high, _ = financing_from_prediction(
        780,
        0.9,
        amounts,
        {
            "on_time_rate": 0.95,
            "payment_consistency": 0.9,
            "default_rate": 0.02,
            "volume_trend": 0.2,
            "transaction_frequency": 6.0,
            "compliance_rate": 0.95,
        },
    )
    assert high > low
    # Strong patterns may exceed historical total money moved
    assert high > total
    assert high <= 50_000_000.0
    assert high != 500_000.0 or low != 500_000.0
