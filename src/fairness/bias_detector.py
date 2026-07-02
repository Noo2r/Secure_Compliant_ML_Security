"""Automatic bias detection: scans computed group/pairwise fairness metrics
and produces structured, textual findings -- largest/smallest disparity,
best/worst-performing group, groups with the highest error rates, and which
disparities are statistically significant (not just numerically nonzero).

Every finding is derived directly from already-computed metrics (no new
statistics invented here) and carries a machine-readable ``finding_type`` +
``supporting_data`` alongside the human-readable description, so
:mod:`fairness_report_builder` can render it without re-deriving anything.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

from src.config.config_loader import FairnessThresholdsConfig
from src.fairness.fairness_metrics import GroupMetrics, PairwiseFairnessMetrics
from src.fairness.statistical_tests import SignificanceTestResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class BiasFinding:
    finding_type: str
    attribute: str
    severity: str  # "info" | "warning" | "critical"
    description: str
    supporting_data: dict

    def to_dict(self) -> dict:
        return asdict(self)


def _severity_for_disparity(abs_value: float, threshold: float) -> str:
    if abs_value > threshold * 2:
        return "critical"
    if abs_value > threshold:
        return "warning"
    return "info"


def detect_bias(
    attribute_name: str,
    group_metrics: dict[str, GroupMetrics],
    pairwise_metrics: dict[str, PairwiseFairnessMetrics],
    significance_result: Optional[SignificanceTestResult],
    thresholds: FairnessThresholdsConfig,
) -> list[BiasFinding]:
    """Runs every automatic check the brief requires and returns one
    ``BiasFinding`` per check (not per group) -- e.g. "largest disparity" is
    a single finding identifying which group has it, not one finding per group.
    """
    findings: list[BiasFinding] = []

    if pairwise_metrics:
        # --- Largest / smallest disparity (by |SPD|) ---
        by_abs_spd = sorted(pairwise_metrics.items(), key=lambda kv: abs(kv[1].statistical_parity_difference))
        smallest_group, smallest = by_abs_spd[0]
        largest_group, largest = by_abs_spd[-1]

        findings.append(BiasFinding(
            finding_type="largest_disparity", attribute=attribute_name,
            severity=_severity_for_disparity(abs(largest.statistical_parity_difference), thresholds.max_acceptable_spd),
            description=(
                f"Largest statistical parity disparity for '{attribute_name}': group '{largest_group}' vs. "
                f"reference '{largest.reference_group}' has SPD={largest.statistical_parity_difference:.4f} "
                f"(95% CI [{largest.spd_ci.ci_lower:.4f}, {largest.spd_ci.ci_upper:.4f}], "
                f"{'statistically significant' if largest.spd_ci.excludes_null else 'NOT statistically significant -- CI includes 0'})."
            ),
            supporting_data={"group": largest_group, "spd": largest.statistical_parity_difference, "ci_excludes_null": largest.spd_ci.excludes_null},
        ))
        findings.append(BiasFinding(
            finding_type="smallest_disparity", attribute=attribute_name, severity="info",
            description=(
                f"Smallest statistical parity disparity for '{attribute_name}': group '{smallest_group}' vs. "
                f"reference '{smallest.reference_group}' has SPD={smallest.statistical_parity_difference:.4f}."
            ),
            supporting_data={"group": smallest_group, "spd": smallest.statistical_parity_difference},
        ))

        # --- Groups whose predictions differ significantly (bootstrap CI excludes null) ---
        significant_groups = [g for g, m in pairwise_metrics.items() if m.spd_ci.excludes_null]
        findings.append(BiasFinding(
            finding_type="statistically_significant_disparities", attribute=attribute_name,
            severity="warning" if significant_groups else "info",
            description=(
                f"{len(significant_groups)} of {len(pairwise_metrics)} group(s) for '{attribute_name}' show a "
                f"selection-rate disparity whose 95% bootstrap CI excludes zero (statistically meaningful, not "
                f"random variation): {significant_groups or 'none'}."
            ),
            supporting_data={"significant_groups": significant_groups, "total_groups_compared": len(pairwise_metrics)},
        ))

        # --- Significance test agreement ---
        findings.append(BiasFinding(
            finding_type="significance_test_result", attribute=attribute_name,
            severity="warning" if significance_result.significant else "info",
            description=(
                f"{significance_result.test_name.replace('_', ' ').title()} test on the "
                f"[{attribute_name} x predicted-label] contingency table: p={significance_result.p_value:.6f} "
                f"({'significant' if significance_result.significant else 'not significant'} at "
                f"alpha={significance_result.alpha}). {significance_result.notes}"
            ),
            supporting_data=significance_result.to_dict(),
        ))

    if group_metrics:
        # --- Best / worst performing group (by F1; balanced_accuracy as tiebreak) ---
        scored = [(g, m) for g, m in group_metrics.items() if m.n_positive_actual > 0]
        if scored:
            best_group, best = max(scored, key=lambda gm: (gm[1].f1, gm[1].balanced_accuracy))
            worst_group, worst = min(scored, key=lambda gm: (gm[1].f1, gm[1].balanced_accuracy))
            findings.append(BiasFinding(
                finding_type="best_performing_group", attribute=attribute_name, severity="info",
                description=f"Best-performing group for '{attribute_name}': '{best_group}' (F1={best.f1:.4f}, recall={best.tpr:.4f}, precision={best.precision:.4f}, n={best.n}).",
                supporting_data={"group": best_group, "f1": best.f1, "recall": best.tpr, "precision": best.precision, "n": best.n},
            ))
            findings.append(BiasFinding(
                finding_type="worst_performing_group", attribute=attribute_name,
                severity="warning" if (best.f1 - worst.f1) > thresholds.max_acceptable_eod else "info",
                description=f"Worst-performing group for '{attribute_name}': '{worst_group}' (F1={worst.f1:.4f}, recall={worst.tpr:.4f}, precision={worst.precision:.4f}, n={worst.n}).",
                supporting_data={"group": worst_group, "f1": worst.f1, "recall": worst.tpr, "precision": worst.precision, "n": worst.n},
            ))
        else:
            findings.append(BiasFinding(
                finding_type="best_performing_group", attribute=attribute_name, severity="info",
                description=f"No group for '{attribute_name}' has any actual positive (fraud) examples in this test set -- best/worst-performing-group comparison is undefined.",
                supporting_data={},
            ))

        # --- Highest false positive / false negative rate groups ---
        fpr_ranked = sorted(group_metrics.items(), key=lambda kv: kv[1].fpr, reverse=True)
        fnr_ranked = sorted(group_metrics.items(), key=lambda kv: kv[1].fnr, reverse=True)
        highest_fpr_group, highest_fpr = fpr_ranked[0]
        highest_fnr_group, highest_fnr = fnr_ranked[0]
        findings.append(BiasFinding(
            finding_type="highest_false_positive_rate_group", attribute=attribute_name,
            severity="warning" if highest_fpr.fpr > thresholds.max_acceptable_spd else "info",
            description=f"Group with the highest false-positive rate for '{attribute_name}': '{highest_fpr_group}' (FPR={highest_fpr.fpr:.4f}, n={highest_fpr.n}) -- legitimate transactions from this group are most often incorrectly flagged as fraud.",
            supporting_data={"group": highest_fpr_group, "fpr": highest_fpr.fpr, "n": highest_fpr.n},
        ))
        findings.append(BiasFinding(
            finding_type="highest_false_negative_rate_group", attribute=attribute_name,
            severity="warning" if highest_fnr.fnr > thresholds.max_acceptable_eod else "info",
            description=f"Group with the highest false-negative rate for '{attribute_name}': '{highest_fnr_group}' (FNR={highest_fnr.fnr:.4f}, n_positive={highest_fnr.n_positive_actual}) -- fraud from this group is most often missed.",
            supporting_data={"group": highest_fnr_group, "fnr": highest_fnr.fnr, "n_positive": highest_fnr.n_positive_actual},
        ))

    logger.info("Bias detection for '%s' produced %d findings.", attribute_name, len(findings))
    return findings
