from app.services.feature_engineering import FEATURE_COLUMNS
from app.services.ml_training import generate_synthetic_training_data, train_models
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
