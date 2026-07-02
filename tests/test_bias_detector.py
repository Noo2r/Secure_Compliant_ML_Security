import numpy as np

from src.config.config_loader import FairnessThresholdsConfig
from src.fairness.bias_detector import detect_bias
from src.fairness.fairness_metrics import compute_group_metrics, compute_pairwise_fairness_metrics
from src.fairness.statistical_tests import run_group_disparity_test

_THRESHOLDS = FairnessThresholdsConfig(
    disparate_impact_low=0.8, disparate_impact_high=1.25,
    max_acceptable_spd=0.10, max_acceptable_eod=0.10, max_acceptable_aod=0.10,
)


def _synthetic_two_group_setup(seed: int = 0):
    rng = np.random.default_rng(seed)
    n = 1000
    y_true = np.concatenate([rng.binomial(1, 0.1, n), rng.binomial(1, 0.1, n)])
    # Group "B" has a much higher predicted-positive rate than "A" -- a real, large disparity.
    y_pred = np.concatenate([rng.binomial(1, 0.10, n), rng.binomial(1, 0.40, n)])
    y_proba = y_pred.astype(float)
    group_labels = np.array(["A"] * n + ["B"] * n)
    return y_true, y_pred, y_proba, group_labels


def test_detect_bias_finds_largest_disparity() -> None:
    y_true, y_pred, y_proba, group_labels = _synthetic_two_group_setup()
    group_metrics = {
        g: compute_group_metrics(y_true[group_labels == g], y_pred[group_labels == g], y_proba[group_labels == g], group=g)
        for g in ("A", "B")
    }
    pairwise = {"B": compute_pairwise_fairness_metrics(y_true, y_pred, group_labels, "B", "A", 300, 0.95, 42)}
    sig = run_group_disparity_test(group_labels, y_pred, alpha=0.05, min_expected_cell_count=5.0)

    findings = detect_bias("test_attr", group_metrics, pairwise, sig, _THRESHOLDS)
    finding_types = [f.finding_type for f in findings]
    assert "largest_disparity" in finding_types
    largest = next(f for f in findings if f.finding_type == "largest_disparity")
    assert largest.supporting_data["group"] == "B"
    assert largest.severity in ("warning", "critical")  # a ~0.30 SPD must be flagged, not "info"


def test_detect_bias_statistically_significant_disparities_flagged() -> None:
    y_true, y_pred, y_proba, group_labels = _synthetic_two_group_setup()
    group_metrics = {
        g: compute_group_metrics(y_true[group_labels == g], y_pred[group_labels == g], y_proba[group_labels == g], group=g)
        for g in ("A", "B")
    }
    pairwise = {"B": compute_pairwise_fairness_metrics(y_true, y_pred, group_labels, "B", "A", 300, 0.95, 42)}
    sig = run_group_disparity_test(group_labels, y_pred, alpha=0.05, min_expected_cell_count=5.0)
    findings = detect_bias("test_attr", group_metrics, pairwise, sig, _THRESHOLDS)
    sig_finding = next(f for f in findings if f.finding_type == "statistically_significant_disparities")
    assert "B" in sig_finding.supporting_data["significant_groups"]


def test_detect_bias_best_worst_performing_group() -> None:
    y_true, y_pred, y_proba, group_labels = _synthetic_two_group_setup()
    group_metrics = {
        g: compute_group_metrics(y_true[group_labels == g], y_pred[group_labels == g], y_proba[group_labels == g], group=g)
        for g in ("A", "B")
    }
    sig = run_group_disparity_test(group_labels, y_pred, alpha=0.05, min_expected_cell_count=5.0)
    findings = detect_bias("test_attr", group_metrics, {}, sig, _THRESHOLDS)
    types = [f.finding_type for f in findings]
    assert "best_performing_group" in types
    assert "worst_performing_group" in types


def test_detect_bias_handles_group_with_no_positive_examples() -> None:
    y_true = np.zeros(50, dtype=int)  # no fraud at all in this group
    y_pred = np.random.default_rng(0).binomial(1, 0.05, size=50)
    y_proba = y_pred.astype(float)
    group_metrics = {"only_group": compute_group_metrics(y_true, y_pred, y_proba, group="only_group")}
    sig = run_group_disparity_test(np.array(["only_group"] * 50), y_pred, alpha=0.05, min_expected_cell_count=5.0)
    findings = detect_bias("test_attr", group_metrics, {}, sig, _THRESHOLDS)
    best_finding = next(f for f in findings if f.finding_type == "best_performing_group")
    assert "undefined" in best_finding.description.lower()


def test_detect_bias_empty_metrics_returns_no_crash() -> None:
    findings = detect_bias("empty_attr", {}, {}, None, _THRESHOLDS)
    assert findings == []
