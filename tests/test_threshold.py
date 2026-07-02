import numpy as np
import pytest

from src.models.threshold import optimize_threshold


@pytest.fixture()
def imbalanced_predictions() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(42)
    n = 2000
    y_true = rng.binomial(1, 0.1, size=n)
    y_proba = np.clip(y_true * 0.6 + rng.normal(0, 0.2, size=n) + 0.1, 0, 1)
    return y_true, y_proba


def test_max_f1_strategy_returns_valid_threshold(imbalanced_predictions) -> None:
    y_true, y_proba = imbalanced_predictions
    decision = optimize_threshold(y_true, y_proba, strategy="max_f1")
    assert 0.0 <= decision.threshold <= 1.0
    assert decision.f1_at_threshold > 0


def test_recall_at_precision_strategy_meets_floor_when_possible(imbalanced_predictions) -> None:
    y_true, y_proba = imbalanced_predictions
    decision = optimize_threshold(y_true, y_proba, strategy="recall_at_precision", min_precision=0.3)
    assert decision.precision_at_threshold >= 0.3 - 1e-9


def test_unknown_strategy_raises() -> None:
    y_true = np.array([0, 1, 0, 1])
    y_proba = np.array([0.1, 0.9, 0.2, 0.8])
    with pytest.raises(ValueError, match="Unknown threshold strategy"):
        optimize_threshold(y_true, y_proba, strategy="not_a_real_strategy")


def test_higher_threshold_strategy_never_exceeds_max_proba(imbalanced_predictions) -> None:
    y_true, y_proba = imbalanced_predictions
    decision = optimize_threshold(y_true, y_proba, strategy="max_f1")
    assert decision.threshold <= y_proba.max()
