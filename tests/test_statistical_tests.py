import numpy as np
import pytest

from src.fairness.statistical_tests import run_group_disparity_test


def test_chi_square_used_when_cochrans_rule_satisfied() -> None:
    rng = np.random.default_rng(0)
    n = 2000
    groups = np.array(["A"] * 1000 + ["B"] * 1000)
    # Large groups with a real difference in predicted-positive rate.
    preds = np.concatenate([rng.binomial(1, 0.3, 1000), rng.binomial(1, 0.1, 1000)])
    result = run_group_disparity_test(groups, preds, alpha=0.05, min_expected_cell_count=5.0)
    assert result.test_name == "chi_square"
    assert result.cochrans_rule_satisfied is True
    assert result.significant is True  # 0.3 vs 0.1 on n=1000 each is a huge, detectable difference


def test_fishers_exact_used_for_small_2x2_table() -> None:
    groups = np.array(["A"] * 3 + ["B"] * 3)
    preds = np.array([1, 0, 0, 0, 0, 0])  # tiny table -> expected counts < 5
    result = run_group_disparity_test(groups, preds, alpha=0.05, min_expected_cell_count=5.0)
    assert result.test_name == "fishers_exact"
    assert result.cochrans_rule_satisfied is False


def test_no_disparity_is_not_significant() -> None:
    rng = np.random.default_rng(1)
    n = 1000
    groups = np.array(["A"] * n + ["B"] * n)
    preds = rng.binomial(1, 0.1, size=2 * n)  # same underlying rate for both groups
    result = run_group_disparity_test(groups, preds, alpha=0.05, min_expected_cell_count=5.0)
    assert result.significant is False


def test_multi_group_table_uses_chi_square_with_caveat_if_rule_violated() -> None:
    groups = np.array(["A"] * 2 + ["B"] * 2 + ["C"] * 2 + ["D"] * 500)
    preds = np.array([1, 0, 1, 0, 0, 0] + [0] * 500)
    result = run_group_disparity_test(groups, preds, alpha=0.05, min_expected_cell_count=5.0)
    assert result.test_name == "chi_square"  # >2 groups -> no exact-test fallback available
    if not result.cochrans_rule_satisfied:
        assert "WARNING" in result.notes or "violated" in result.notes.lower()


def test_missing_group_values_are_excluded_not_crashed() -> None:
    groups = np.array(["A", "A", None, "B", "B", np.nan], dtype=object)
    preds = np.array([1, 0, 1, 0, 1, 0])
    result = run_group_disparity_test(groups, preds, alpha=0.05, min_expected_cell_count=5.0)
    # Only 4 valid (non-null) rows contribute to the contingency table.
    assert sum(sum(row) for row in result.contingency_table) == 4


def test_to_dict_is_json_serializable_shape() -> None:
    groups = np.array(["A"] * 100 + ["B"] * 100)
    preds = np.random.default_rng(0).binomial(1, 0.2, size=200)
    result = run_group_disparity_test(groups, preds, alpha=0.05, min_expected_cell_count=5.0)
    d = result.to_dict()
    assert isinstance(d["contingency_table"], list)
    assert isinstance(d["p_value"], float)
