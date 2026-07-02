import numpy as np
import pytest

from src.evaluation.metrics import (
    compute_calibration_curve,
    compute_classification_metrics,
    compute_confusion_matrix,
    lift_and_gain,
    precision_at_k,
    recall_at_precision,
)


@pytest.fixture()
def perfectly_separable() -> tuple[np.ndarray, np.ndarray]:
    y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    y_proba = np.array([0.05, 0.1, 0.15, 0.2, 0.8, 0.85, 0.9, 0.95])
    return y_true, y_proba


def test_classification_metrics_perfect_separation(perfectly_separable) -> None:
    y_true, y_proba = perfectly_separable
    metrics = compute_classification_metrics(y_true, y_proba, threshold=0.5)
    assert metrics.accuracy == 1.0
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.f1 == 1.0
    assert metrics.roc_auc == 1.0
    assert metrics.pr_auc == 1.0


def test_confusion_matrix_perfect_separation(perfectly_separable) -> None:
    y_true, y_proba = perfectly_separable
    cm = compute_confusion_matrix(y_true, y_proba, threshold=0.5)
    assert cm == {"true_negative": 4, "false_positive": 0, "false_negative": 0, "true_positive": 4}


def test_precision_at_k_top_k_all_fraud() -> None:
    y_true = np.array([1, 1, 0, 0, 0])
    y_proba = np.array([0.9, 0.8, 0.3, 0.2, 0.1])  # top 2 by score are exactly the 2 frauds
    result = precision_at_k(y_true, y_proba, k=2)
    assert result["precision_at_k"] == 1.0
    assert result["frauds_captured"] == 2


def test_precision_at_k_caps_k_at_population_size() -> None:
    y_true = np.array([1, 0])
    y_proba = np.array([0.9, 0.1])
    result = precision_at_k(y_true, y_proba, k=1000)
    assert result["k"] == 2


def test_recall_at_precision_meets_target(perfectly_separable) -> None:
    y_true, y_proba = perfectly_separable
    result = recall_at_precision(y_true, y_proba, min_precision=0.9)
    assert result["target_met"] is True
    assert result["achieved_precision"] >= 0.9
    assert result["recall"] == pytest.approx(1.0)


def test_recall_at_precision_unreachable_target_falls_back() -> None:
    # Highest-scored point (index 0, proba=0.9) is a FALSE positive, so even
    # the most conservative threshold (predict only that point) has 0%
    # precision -- no threshold on this sample can reach 99.99% precision.
    y_true = np.array([0, 1, 0, 1, 0])
    y_proba = np.array([0.9, 0.6, 0.5, 0.55, 0.45])
    result = recall_at_precision(y_true, y_proba, min_precision=0.9999)
    assert result["target_met"] is False


def test_lift_and_gain_top_decile_captures_more_than_random() -> None:
    rng = np.random.default_rng(0)
    n = 1000
    y_true = rng.binomial(1, 0.1, size=n)
    # Make predicted probability strongly correlated with the true label.
    y_proba = y_true * 0.8 + rng.uniform(0, 0.2, size=n)
    table = lift_and_gain(y_true, y_proba, n_bins=10)
    assert len(table) == 10
    # A good model's top decile should have lift well above 1 (better than random).
    assert table.iloc[0]["lift"] > 1.0
    # Gain must be monotonically non-decreasing as more population is reviewed.
    assert (table["gain"].diff().dropna() >= 0).all()
    assert table.iloc[-1]["gain"] == pytest.approx(1.0)


def test_calibration_curve_shape() -> None:
    rng = np.random.default_rng(1)
    y_true = rng.binomial(1, 0.3, size=500)
    y_proba = rng.uniform(0, 1, size=500)
    prob_true, prob_pred = compute_calibration_curve(y_true, y_proba, n_bins=5)
    assert len(prob_true) == len(prob_pred)
    assert len(prob_true) <= 5
