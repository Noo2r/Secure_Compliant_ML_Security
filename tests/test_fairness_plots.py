import numpy as np
import pandas as pd

from src.config.config_loader import FairnessStatisticsConfig, FairnessThresholdsConfig, ProtectedAttributeConfig
from src.fairness.attribute_analysis import analyze_protected_attribute
from src.fairness.fairness_plots import (
    plot_disparate_impact,
    plot_error_rate_comparison,
    plot_fairness_dashboard,
    plot_fairness_metric_bars,
    plot_group_confusion_matrices,
    plot_pr_per_group,
    plot_roc_per_group,
    plot_selection_rate_comparison,
)

_STATS_CFG = FairnessStatisticsConfig(
    bootstrap_iterations=50, bootstrap_confidence_level=0.95, significance_alpha=0.05,
    min_expected_cell_count_for_chi_square=5.0, random_state=42,
)
_THRESHOLDS = FairnessThresholdsConfig(
    disparate_impact_low=0.8, disparate_impact_high=1.25,
    max_acceptable_spd=0.10, max_acceptable_eod=0.10, max_acceptable_aod=0.10,
)


def _build_result():
    rng = np.random.default_rng(0)
    n = 400
    y_true = rng.binomial(1, 0.1, size=n)
    y_pred = rng.binomial(1, 0.15, size=n)
    y_proba = rng.uniform(size=n)
    raw_groups = pd.Series(rng.choice(["debit", "credit"], size=n))
    attr_cfg = ProtectedAttributeConfig(name="card6", description="test", reference_group="debit", primary=True)
    return analyze_protected_attribute(
        y_true, y_pred, y_proba, raw_groups, attr_cfg, _STATS_CFG, _THRESHOLDS,
        fairlearn_enabled=False, fairlearn_tolerance=1e-6,
    ), y_true, y_proba, raw_groups


def test_all_plot_functions_produce_files(tmp_path) -> None:
    result, y_true, y_proba, raw_groups = _build_result()
    dpi = 60

    plot_selection_rate_comparison(result.group_metrics, "card6", tmp_path / "sel.png", dpi)
    plot_error_rate_comparison(result.group_metrics, "card6", tmp_path / "err.png", dpi)
    plot_group_confusion_matrices(result.group_metrics, "card6", tmp_path / "cm.png", dpi)
    plot_fairness_metric_bars(result.pairwise_metrics, "card6", tmp_path / "bars.png", dpi)
    plot_disparate_impact(result.pairwise_metrics, "card6", 0.8, 1.25, tmp_path / "di.png", dpi)
    plot_fairness_dashboard(result.group_metrics, result.pairwise_metrics, "card6", tmp_path / "dash.png", dpi)

    filled = raw_groups.astype(object).where(raw_groups.notna(), "Missing")
    y_true_by_group = {g: y_true[filled == g] for g in filled.unique()}
    y_proba_by_group = {g: y_proba[filled == g] for g in filled.unique()}
    plot_roc_per_group(y_true_by_group, y_proba_by_group, "card6", tmp_path / "roc.png", dpi)
    plot_pr_per_group(y_true_by_group, y_proba_by_group, "card6", tmp_path / "pr.png", dpi)

    for name in ("sel.png", "err.png", "cm.png", "bars.png", "di.png", "dash.png", "roc.png", "pr.png"):
        assert (tmp_path / name).exists()
        assert (tmp_path / name).stat().st_size > 0


def test_plot_dashboard_handles_empty_pairwise_metrics(tmp_path) -> None:
    result, _, _, _ = _build_result()
    plot_fairness_dashboard(result.group_metrics, {}, "card6", tmp_path / "dash_no_pairwise.png", 60)
    assert (tmp_path / "dash_no_pairwise.png").exists()


def test_plot_roc_per_group_skips_single_class_group_without_crashing(tmp_path) -> None:
    y_true_by_group = {
        "all_negative": np.zeros(20, dtype=int),
        "mixed": np.array([0, 1] * 10),
    }
    y_proba_by_group = {
        "all_negative": np.random.default_rng(0).uniform(size=20),
        "mixed": np.random.default_rng(1).uniform(size=20),
    }
    plot_roc_per_group(y_true_by_group, y_proba_by_group, "test", tmp_path / "roc_mixed.png", 60)
    assert (tmp_path / "roc_mixed.png").exists()
