import numpy as np
import pytest

from src.fairness.fairness_metrics import (
    ConfidenceInterval,
    GroupMetrics,
    bootstrap_confidence_interval,
    compute_group_metrics,
    compute_pairwise_fairness_metrics,
)


def test_compute_group_metrics_correctness_against_hand_computed_values() -> None:
    # 10 examples: 4 true positives, 1 false positive, 2 false negatives, 3 true negatives
    y_true = np.array([1, 1, 1, 1, 1, 1, 0, 0, 0, 0])
    y_pred = np.array([1, 1, 1, 1, 0, 0, 1, 0, 0, 0])
    y_proba = y_pred.astype(float)
    m = compute_group_metrics(y_true, y_pred, y_proba, group="test")
    assert m.confusion_matrix == {"true_negative": 3, "false_positive": 1, "false_negative": 2, "true_positive": 4}
    assert m.tpr == pytest.approx(4 / 6)
    assert m.fpr == pytest.approx(1 / 4)
    assert m.fnr == pytest.approx(2 / 6)
    assert m.tnr == pytest.approx(3 / 4)
    assert m.precision == pytest.approx(4 / 5)
    assert m.selection_rate == pytest.approx(5 / 10)
    assert m.n == 10
    assert m.n_positive_actual == 6


def test_compute_group_metrics_empty_group_does_not_crash() -> None:
    y_true = np.array([], dtype=int)
    y_pred = np.array([], dtype=int)
    y_proba = np.array([], dtype=float)
    m = compute_group_metrics(y_true, y_pred, y_proba, group="empty")
    assert m.n == 0
    assert m.selection_rate == 0.0
    assert m.tpr == 0.0
    assert m.roc_auc is None
    assert m.pr_auc is None


def test_compute_group_metrics_single_class_group_returns_none_auc() -> None:
    y_true = np.zeros(20, dtype=int)  # all negative -- only one true class
    y_pred = np.array([0] * 18 + [1] * 2)
    y_proba = np.random.default_rng(0).uniform(size=20)
    m = compute_group_metrics(y_true, y_pred, y_proba, group="single_class")
    assert m.roc_auc is None
    assert m.pr_auc is None
    assert m.n_positive_actual == 0
    assert m.tpr == 0.0  # 0/0 -> 0.0, not NaN or crash


def test_compute_group_metrics_no_predicted_positives_precision_is_zero_not_nan() -> None:
    y_true = np.array([1, 0, 1, 0])
    y_pred = np.array([0, 0, 0, 0])  # nothing predicted positive
    y_proba = np.array([0.1, 0.2, 0.3, 0.1])
    m = compute_group_metrics(y_true, y_pred, y_proba, group="no_positive_preds")
    assert m.precision == 0.0
    assert not np.isnan(m.precision)
    assert m.f1 == 0.0


def test_compute_group_metrics_all_correct_predictions() -> None:
    y_true = np.array([1, 1, 0, 0])
    y_pred = np.array([1, 1, 0, 0])
    y_proba = np.array([0.9, 0.8, 0.1, 0.2])
    m = compute_group_metrics(y_true, y_pred, y_proba, group="perfect")
    assert m.tpr == 1.0
    assert m.fpr == 0.0
    assert m.precision == 1.0
    assert m.f1 == 1.0
    assert m.roc_auc == 1.0


def test_bootstrap_confidence_interval_excludes_null_for_large_true_disparity() -> None:
    rng = np.random.default_rng(42)
    n = 2000
    # Group A: 30% selection rate; Group B (reference): 5% selection rate -- a large, real disparity
    y_true_a = rng.binomial(1, 0.1, size=n)
    y_pred_a = rng.binomial(1, 0.30, size=n)
    y_true_b = rng.binomial(1, 0.1, size=n)
    y_pred_b = rng.binomial(1, 0.05, size=n)

    def spd(gd):
        rate_a = gd["group"][1].mean()
        rate_b = gd["reference"][1].mean()
        return rate_a - rate_b

    ci = bootstrap_confidence_interval(
        {"group": (y_true_a, y_pred_a), "reference": (y_true_b, y_pred_b)},
        spd, n_iterations=500, confidence_level=0.95, random_state=42, null_value=0.0,
    )
    assert isinstance(ci, ConfidenceInterval)
    assert ci.point_estimate == pytest.approx(0.25, abs=0.03)
    assert ci.excludes_null is True  # a disparity this large must be statistically detectable


def test_bootstrap_confidence_interval_includes_null_for_identical_groups() -> None:
    rng = np.random.default_rng(1)
    n = 500
    y_true = rng.binomial(1, 0.1, size=n)
    y_pred = rng.binomial(1, 0.1, size=n)

    def spd(gd):
        return gd["group"][1].mean() - gd["reference"][1].mean()

    # Same underlying data for both "group" and "reference" -- true disparity is exactly 0.
    ci = bootstrap_confidence_interval(
        {"group": (y_true, y_pred), "reference": (y_true.copy(), y_pred.copy())},
        spd, n_iterations=500, confidence_level=0.95, random_state=1, null_value=0.0,
    )
    assert ci.point_estimate == 0.0
    assert ci.excludes_null is False


def test_compute_pairwise_fairness_metrics_end_to_end() -> None:
    rng = np.random.default_rng(7)
    n = 1000
    y_true = rng.binomial(1, 0.1, size=n)
    y_pred = rng.binomial(1, 0.15, size=n)
    group_labels = np.array(["A"] * 500 + ["B"] * 500)

    result = compute_pairwise_fairness_metrics(
        y_true, y_pred, group_labels, group="B", reference_group="A",
        n_bootstrap=200, confidence_level=0.95, random_state=42,
    )
    assert result.group == "B"
    assert result.reference_group == "A"
    assert result.n_group == 500
    assert result.n_reference == 500
    assert isinstance(result.spd_ci, ConfidenceInterval)


def test_disparate_impact_ratio_nan_when_reference_selection_rate_is_zero() -> None:
    y_true = np.array([0, 0, 1, 1])
    y_pred = np.array([1, 1, 0, 0])  # group selects, reference selects nothing
    group_labels = np.array(["group", "group", "reference", "reference"])
    result = compute_pairwise_fairness_metrics(
        y_true, y_pred, group_labels, group="group", reference_group="reference",
        n_bootstrap=50, confidence_level=0.95, random_state=1,
    )
    # Reference selection rate is 0 -> DIR is mathematically undefined (division by zero),
    # must be NaN, not a crash or a misleading 0/inf.
    assert np.isnan(result.disparate_impact_ratio)
