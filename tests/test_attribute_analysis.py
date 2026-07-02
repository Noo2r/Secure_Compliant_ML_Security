import numpy as np
import pandas as pd
import pytest

from src.config.config_loader import (
    FairnessStatisticsConfig,
    FairnessThresholdsConfig,
    ProtectedAttributeConfig,
)
from src.fairness.attribute_analysis import analyze_protected_attribute

_STATS_CFG = FairnessStatisticsConfig(
    bootstrap_iterations=100, bootstrap_confidence_level=0.95, significance_alpha=0.05,
    min_expected_cell_count_for_chi_square=5.0, random_state=42,
)
_THRESHOLDS = FairnessThresholdsConfig(
    disparate_impact_low=0.8, disparate_impact_high=1.25,
    max_acceptable_spd=0.10, max_acceptable_eod=0.10, max_acceptable_aod=0.10,
)


def _synthetic_data(seed: int = 0, with_missing: bool = True):
    rng = np.random.default_rng(seed)
    n = 600
    y_true = rng.binomial(1, 0.1, size=n)
    y_pred = rng.binomial(1, 0.15, size=n)
    y_proba = rng.uniform(size=n)
    raw_groups = pd.Series(rng.choice(["debit", "credit"], size=n))
    if with_missing:
        missing_idx = rng.choice(n, size=30, replace=False)
        raw_groups.iloc[missing_idx] = np.nan
    return y_true, y_pred, y_proba, raw_groups


def test_analyze_protected_attribute_handles_missing_values_as_explicit_group() -> None:
    y_true, y_pred, y_proba, raw_groups = _synthetic_data(with_missing=True)
    attr_cfg = ProtectedAttributeConfig(
        name="card6", description="test", reference_group="debit", primary=True,
    )
    result = analyze_protected_attribute(
        y_true, y_pred, y_proba, raw_groups, attr_cfg, _STATS_CFG, _THRESHOLDS,
        fairlearn_enabled=False, fairlearn_tolerance=1e-6,
    )
    assert "Missing" in result.group_metrics
    assert result.group_metrics["Missing"].n == 30
    # "Missing" must never appear as a pairwise-comparison group (not a meaningful protected contrast).
    assert "Missing" not in result.pairwise_metrics


def test_analyze_protected_attribute_reference_group_excluded_from_pairwise() -> None:
    y_true, y_pred, y_proba, raw_groups = _synthetic_data(with_missing=False)
    attr_cfg = ProtectedAttributeConfig(name="card6", description="test", reference_group="debit", primary=True)
    result = analyze_protected_attribute(
        y_true, y_pred, y_proba, raw_groups, attr_cfg, _STATS_CFG, _THRESHOLDS,
        fairlearn_enabled=False, fairlearn_tolerance=1e-6,
    )
    assert "debit" not in result.pairwise_metrics
    assert "credit" in result.pairwise_metrics


def test_analyze_protected_attribute_missing_reference_group_skips_pairwise_gracefully() -> None:
    y_true, y_pred, y_proba, raw_groups = _synthetic_data(with_missing=False)
    attr_cfg = ProtectedAttributeConfig(
        name="card6", description="test", reference_group="does_not_exist_in_data", primary=True,
    )
    result = analyze_protected_attribute(
        y_true, y_pred, y_proba, raw_groups, attr_cfg, _STATS_CFG, _THRESHOLDS,
        fairlearn_enabled=False, fairlearn_tolerance=1e-6,
    )
    assert result.pairwise_metrics == {}
    assert result.group_metrics  # group metrics still computed even without a valid reference


def test_analyze_protected_attribute_produces_bias_findings() -> None:
    y_true, y_pred, y_proba, raw_groups = _synthetic_data(with_missing=True)
    attr_cfg = ProtectedAttributeConfig(name="card6", description="test", reference_group="debit", primary=True)
    result = analyze_protected_attribute(
        y_true, y_pred, y_proba, raw_groups, attr_cfg, _STATS_CFG, _THRESHOLDS,
        fairlearn_enabled=False, fairlearn_tolerance=1e-6,
    )
    assert len(result.bias_findings) > 0
    assert result.significance_result is not None
