import numpy as np
import pytest

from src.models.model_registry import compute_scale_pos_weight, get_model_spec

_ALL_MODELS = ["logistic_regression", "random_forest", "xgboost", "lightgbm", "neural_network"]


@pytest.mark.parametrize("name", _ALL_MODELS)
def test_get_model_spec_returns_buildable_estimator(name: str) -> None:
    spec = get_model_spec(name)
    assert spec.name == name

    class _FakeTrial:
        def suggest_float(self, name, low, high, log=False, step=None):
            return (low + high) / 2

        def suggest_int(self, name, low, high, step=1):
            return low

        def suggest_categorical(self, name, choices):
            return choices[0]

    params = spec.suggest_params(_FakeTrial())
    estimator = spec.build_estimator(params, scale_pos_weight=5.0, random_state=42)
    assert hasattr(estimator, "fit")
    assert hasattr(estimator, "predict_proba")


def test_get_model_spec_unknown_name_raises() -> None:
    with pytest.raises(ValueError, match="Unknown candidate model"):
        get_model_spec("not_a_real_model")


def test_compute_scale_pos_weight_matches_manual_ratio() -> None:
    y = np.array([0, 0, 0, 0, 0, 0, 0, 0, 1, 1])  # 8 negative, 2 positive
    assert compute_scale_pos_weight(y) == pytest.approx(4.0)


def test_compute_scale_pos_weight_handles_no_positives_without_dividing_by_zero() -> None:
    y = np.array([0, 0, 0])
    weight = compute_scale_pos_weight(y)
    # positive_count floors at 1 (avoids ZeroDivisionError): (3 - 1) / 1 = 2.0
    assert weight == pytest.approx(2.0)
