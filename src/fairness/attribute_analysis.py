"""Runs the complete fairness analysis for ONE protected/proxy attribute:
per-group metrics, pairwise fairness metrics vs. the reference group,
significance testing, bias detection, and (optionally) Fairlearn
cross-validation. The single entry point every attribute in
``scripts/run_module5.py`` goes through, so every attribute is analyzed
with identical methodology.

Missing/NaN group values are treated as an explicit ``"Missing"`` group
(not silently dropped) -- for ``DeviceType`` in particular, 80%+ of the test
set is missing, and whether missing-device transactions are scored
differently is itself a valid, honest fairness question. ``"Missing"`` is
included in group-wise metrics and the significance test, but excluded from
pairwise SPD/DIR/EOD/AOD comparisons against the reference group (comparing
"unknown device" to "desktop" is not a meaningful protected-group contrast
in the traditional sense).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.config.config_loader import FairnessStatisticsConfig, ProtectedAttributeConfig
from src.fairness.bias_detector import detect_bias
from src.fairness.fairlearn_validation import cross_check_against_fairlearn
from src.fairness.fairness_metrics import compute_group_metrics, compute_pairwise_fairness_metrics
from src.fairness.fairness_report_builder import AttributeFairnessResult
from src.fairness.statistical_tests import run_group_disparity_test
from src.utils.logger import get_logger

logger = get_logger(__name__)

_MISSING_LABEL = "Missing"


def analyze_protected_attribute(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray,
    raw_group_values: pd.Series,
    attribute_config: ProtectedAttributeConfig,
    statistics_config: FairnessStatisticsConfig,
    fairness_thresholds,
    fairlearn_enabled: bool,
    fairlearn_tolerance: float,
) -> AttributeFairnessResult:
    group_labels = raw_group_values.astype(object).where(raw_group_values.notna(), _MISSING_LABEL).to_numpy()
    unique_groups = sorted(np.unique(group_labels).tolist())
    logger.info(
        "Analyzing attribute '%s': %d groups %s (missing=%d rows, %.1f%%)",
        attribute_config.name, len(unique_groups), unique_groups,
        int((group_labels == _MISSING_LABEL).sum()), float((group_labels == _MISSING_LABEL).mean() * 100),
    )

    group_metrics = {}
    for g in unique_groups:
        mask = group_labels == g
        group_metrics[g] = compute_group_metrics(y_true[mask], y_pred[mask], y_proba[mask], group=g)

    reference = attribute_config.reference_group
    comparable_groups = [g for g in unique_groups if g != _MISSING_LABEL and g != reference]
    pairwise_metrics = {}
    if reference in unique_groups:
        for g in comparable_groups:
            pairwise_metrics[g] = compute_pairwise_fairness_metrics(
                y_true, y_pred, group_labels, group=g, reference_group=reference,
                n_bootstrap=statistics_config.bootstrap_iterations,
                confidence_level=statistics_config.bootstrap_confidence_level,
                random_state=statistics_config.random_state,
            )
    else:
        logger.warning(
            "Reference group '%s' not present in the data for '%s' -- skipping pairwise fairness metrics.",
            reference, attribute_config.name,
        )

    significance_result = run_group_disparity_test(
        group_labels, y_pred, alpha=statistics_config.significance_alpha,
        min_expected_cell_count=statistics_config.min_expected_cell_count_for_chi_square,
    )

    bias_findings = detect_bias(
        attribute_config.name, group_metrics, pairwise_metrics, significance_result, fairness_thresholds
    )

    fairlearn_results = []
    if fairlearn_enabled and pairwise_metrics and reference in unique_groups:
        first_group = comparable_groups[0] if comparable_groups else None
        if first_group is not None:
            own_selection_rates = {g: m.selection_rate for g, m in group_metrics.items()}
            fairlearn_results = cross_check_against_fairlearn(
                y_true, y_pred, group_labels, own_selection_rates,
                own_spd=pairwise_metrics[first_group].statistical_parity_difference,
                own_dir=pairwise_metrics[first_group].disparate_impact_ratio,
                group=first_group, reference_group=reference, tolerance=fairlearn_tolerance,
            )

    return AttributeFairnessResult(
        attribute_name=attribute_config.name,
        description=attribute_config.description,
        reference_group=reference,
        excluded_from_primary=attribute_config.excluded_from_primary_analysis,
        group_metrics=group_metrics,
        pairwise_metrics=pairwise_metrics,
        significance_result=significance_result,
        bias_findings=bias_findings,
        fairlearn_cross_check=fairlearn_results,
    )
