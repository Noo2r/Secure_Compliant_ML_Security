import numpy as np
import pytest

from src.fairness.fairlearn_validation import cross_check_against_fairlearn, is_fairlearn_available

pytestmark = pytest.mark.skipif(not is_fairlearn_available(), reason="fairlearn not installed")


def test_cross_check_selection_rate_matches_fairlearn_exactly() -> None:
    rng = np.random.default_rng(0)
    n = 2000
    y_true = rng.binomial(1, 0.1, size=n)
    y_pred = np.concatenate([rng.binomial(1, 0.2, n // 2), rng.binomial(1, 0.05, n // 2)])
    group_labels = np.array(["A"] * (n // 2) + ["B"] * (n // 2))

    own_rates = {
        "A": float(y_pred[group_labels == "A"].mean()),
        "B": float(y_pred[group_labels == "B"].mean()),
    }
    own_spd = own_rates["B"] - own_rates["A"]
    own_dir = own_rates["B"] / own_rates["A"] if own_rates["A"] > 0 else float("nan")

    results = cross_check_against_fairlearn(
        y_true, y_pred, group_labels, own_rates, own_spd, own_dir,
        group="B", reference_group="A", tolerance=1e-6,
    )
    assert all(r.available for r in results)
    selection_rate_results = [r for r in results if r.metric_name.startswith("selection_rate")]
    assert len(selection_rate_results) == 2
    for r in selection_rate_results:
        assert r.within_tolerance is True, f"{r.metric_name}: own={r.own_value} fairlearn={r.fairlearn_value}"


def test_cross_check_spd_agrees_with_fairlearn_in_absolute_value() -> None:
    rng = np.random.default_rng(1)
    n = 1000
    y_true = rng.binomial(1, 0.1, size=n)
    y_pred = np.concatenate([rng.binomial(1, 0.3, n // 2), rng.binomial(1, 0.1, n // 2)])
    group_labels = np.array(["A"] * (n // 2) + ["B"] * (n // 2))

    rate_a = float(y_pred[group_labels == "A"].mean())
    rate_b = float(y_pred[group_labels == "B"].mean())
    own_spd = rate_a - rate_b  # signed, group="A" vs reference="B"
    own_dir = rate_a / rate_b if rate_b > 0 else float("nan")

    results = cross_check_against_fairlearn(
        y_true, y_pred, group_labels, {"A": rate_a, "B": rate_b}, own_spd, own_dir,
        group="A", reference_group="B", tolerance=1e-6,
    )
    spd_result = next(r for r in results if "statistical_parity" in r.metric_name)
    assert spd_result.within_tolerance is True
