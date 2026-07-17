from app.services.ml_training import generate_synthetic_training_data, train_models


def test_synthetic_data_shape():
    df, labels = generate_synthetic_training_data(n_samples=200, random_seed=42)
    assert len(df) == 200
    assert len(labels) == 200
    assert set(labels).issubset({0, 1})


def test_train_models_rf_outperforms():
    results = train_models(db_session=None)
    assert "rf_metrics" in results
    assert "lr_metrics" in results
    assert results["rf_metrics"]["roc_auc"] > 0.5
    assert results["lr_metrics"]["roc_auc"] > 0.5
    # RF should generally outperform on this synthetic non-linear data
    assert results["rf_outperforms_baseline"] is True
