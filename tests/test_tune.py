import numpy as np

from src.models.model_registry import get_model_spec
from src.models.tune import HyperparameterTuner, sample_time_ordered


def test_sample_time_ordered_returns_full_data_when_n_exceeds_length() -> None:
    X = np.arange(10).reshape(-1, 1)
    y = np.arange(10)
    X_sample, y_sample = sample_time_ordered(X, y, n=100)
    assert len(X_sample) == 10
    np.testing.assert_array_equal(X_sample, X)


def test_sample_time_ordered_preserves_chronological_order() -> None:
    X = np.arange(100).reshape(-1, 1)
    y = np.zeros(100)
    X_sample, _ = sample_time_ordered(X, y, n=10)
    assert len(X_sample) == 10
    # Sampled indices must be strictly increasing (time order preserved).
    assert np.all(np.diff(X_sample.ravel()) > 0)


def test_hyperparameter_tuner_runs_end_to_end_on_logistic_regression() -> None:
    rng = np.random.default_rng(42)
    n = 300
    X = rng.normal(size=(n, 3))
    y = (X[:, 0] + rng.normal(scale=0.1, size=n) > 0).astype(int)

    tuner = HyperparameterTuner(
        model_spec=get_model_spec("logistic_regression"),
        cv_folds=2,
        n_trials=3,
        timeout_seconds=60,
        random_state=42,
    )
    result = tuner.tune(X, y)
    assert result.model_name == "logistic_regression"
    assert 0.0 <= result.best_cv_score <= 1.0
    assert len(result.cv_fold_scores) == 2
    assert "C" in result.best_params
