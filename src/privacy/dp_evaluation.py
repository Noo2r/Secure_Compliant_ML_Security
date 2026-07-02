"""Normal-vs-DP evaluation and privacy-utility tradeoff analysis.

Reuses Module 3's evaluation primitives directly (``src.evaluation.metrics``,
``src.models.threshold``) rather than reimplementing metric computation --
the Normal and DP models are just two more classifiers evaluated the exact
same way every Module 3 candidate was.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.evaluation.metrics import (
    ClassificationMetrics,
    compute_classification_metrics,
    compute_confusion_matrix,
    compute_pr_curve,
    compute_roc_curve,
)
from src.models.threshold import ThresholdDecision, optimize_threshold
from src.privacy.privacy_accountant import PrivacyBudget
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class DPComparisonResult:
    normal_metrics: ClassificationMetrics
    dp_metrics: ClassificationMetrics
    normal_threshold: ThresholdDecision
    dp_threshold: ThresholdDecision
    normal_confusion_matrix: dict
    dp_confusion_matrix: dict
    normal_roc_curve: tuple
    dp_roc_curve: tuple
    normal_pr_curve: tuple
    dp_pr_curve: tuple
    metric_deltas: dict[str, float]  # normal - dp, per metric
    explanation: str


def evaluate_and_compare(
    y_val: np.ndarray,
    normal_proba_val: np.ndarray,
    dp_proba_val: np.ndarray,
    y_test: np.ndarray,
    normal_proba_test: np.ndarray,
    dp_proba_test: np.ndarray,
    privacy_budget: PrivacyBudget,
    l2_norm_clip: float,
    threshold_strategy: str = "max_f1",
    threshold_min_precision: float = 0.5,
) -> DPComparisonResult:
    """Thresholds both models independently (each on its own validation
    predictions, never the test set), evaluates both on the same held-out
    test set, and builds a data-driven explanation of the observed gap.
    """
    normal_threshold = optimize_threshold(y_val, normal_proba_val, threshold_strategy, threshold_min_precision)
    dp_threshold = optimize_threshold(y_val, dp_proba_val, threshold_strategy, threshold_min_precision)

    normal_metrics = compute_classification_metrics(y_test, normal_proba_test, normal_threshold.threshold)
    dp_metrics = compute_classification_metrics(y_test, dp_proba_test, dp_threshold.threshold)

    normal_cm = compute_confusion_matrix(y_test, normal_proba_test, normal_threshold.threshold)
    dp_cm = compute_confusion_matrix(y_test, dp_proba_test, dp_threshold.threshold)

    normal_roc = compute_roc_curve(y_test, normal_proba_test)
    dp_roc = compute_roc_curve(y_test, dp_proba_test)
    normal_pr = compute_pr_curve(y_test, normal_proba_test)
    dp_pr = compute_pr_curve(y_test, dp_proba_test)

    deltas = {
        field: getattr(normal_metrics, field) - getattr(dp_metrics, field)
        for field in ("accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc")
    }

    explanation = _build_explanation(normal_metrics, dp_metrics, deltas, privacy_budget, l2_norm_clip)

    result = DPComparisonResult(
        normal_metrics=normal_metrics,
        dp_metrics=dp_metrics,
        normal_threshold=normal_threshold,
        dp_threshold=dp_threshold,
        normal_confusion_matrix=normal_cm,
        dp_confusion_matrix=dp_cm,
        normal_roc_curve=normal_roc,
        dp_roc_curve=dp_roc,
        normal_pr_curve=normal_pr,
        dp_pr_curve=dp_pr,
        metric_deltas=deltas,
        explanation=explanation,
    )
    logger.info(
        "Normal vs DP: PR-AUC %.4f -> %.4f (delta=%.4f), ROC-AUC %.4f -> %.4f (delta=%.4f)",
        normal_metrics.pr_auc, dp_metrics.pr_auc, deltas["pr_auc"],
        normal_metrics.roc_auc, dp_metrics.roc_auc, deltas["roc_auc"],
    )
    return result


def _build_explanation(
    normal: ClassificationMetrics,
    dp: ClassificationMetrics,
    deltas: dict[str, float],
    budget: PrivacyBudget,
    l2_norm_clip: float,
) -> str:
    """Generates a data-driven (not templated-fluff) explanation of the
    observed Normal-vs-DP gap, referencing the actual numbers computed.
    """
    pr_auc_drop_pct = (deltas["pr_auc"] / normal.pr_auc * 100) if normal.pr_auc > 0 else float("nan")
    direction = "dropped" if deltas["pr_auc"] > 0 else "did not drop (or improved)"

    lines = [
        f"PR-AUC {direction} from {normal.pr_auc:.4f} (Normal) to {dp.pr_auc:.4f} (DP), "
        f"a {pr_auc_drop_pct:.1f}% relative change, at privacy budget epsilon={budget.epsilon:.3f}, "
        f"delta={budget.delta:.1e}.",
        "",
        "This gap is expected and mechanistically explained by DP-SGD's two departures from "
        "normal training, both active here:",
        f"1. Per-example gradient clipping to L2 norm {l2_norm_clip} discards gradient magnitude "
        "information above that bound -- any example whose true gradient is larger gets "
        "projected down, losing information about how strongly it should influence the update.",
        f"2. Calibrated Gaussian noise with standard deviation {budget.noise_multiplier} x "
        f"{l2_norm_clip} = {budget.noise_multiplier * l2_norm_clip:.3f} is added to the summed "
        "clipped gradients every step, directly degrading gradient signal quality in exchange "
        "for the formal privacy guarantee.",
        "Both effects compound over training steps, so more epochs/steps at a fixed "
        "noise_multiplier accumulate more total noise exposure (and a larger epsilon) without "
        "necessarily improving DP model quality the way more epochs typically helps normal "
        "training.",
    ]

    if abs(deltas["recall"]) > abs(deltas["precision"]):
        lines.append(
            f"The gap is more pronounced in recall (delta={deltas['recall']:.4f}) than precision "
            f"(delta={deltas['precision']:.4f}), consistent with noise disproportionately harming "
            "the model's ability to confidently identify the minority (fraud) class, whose "
            "already-sparse gradient signal is more easily swamped by added noise than the "
            "majority class's abundant signal."
        )
    else:
        lines.append(
            f"The gap is more pronounced in precision (delta={deltas['precision']:.4f}) than recall "
            f"(delta={deltas['recall']:.4f})."
        )

    return "\n".join(lines)
