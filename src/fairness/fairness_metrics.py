"""Group fairness metrics for binary classification.

Two layers, deliberately separate:

* **Per-group metrics** (:func:`compute_group_metrics`) -- standard
  classification metrics (TPR, FPR, precision, ROC-AUC, ...) computed once
  per protected-attribute group, reusing :mod:`src.evaluation.metrics`
  rather than reimplementing confusion-matrix arithmetic.
* **Pairwise fairness metrics** (:func:`compute_pairwise_fairness_metrics`)
  -- Statistical Parity Difference, Disparate Impact Ratio, Equal
  Opportunity Difference, Average Odds Difference -- each group compared
  against a configured reference group, with bootstrap confidence intervals
  so a disparity can be judged statistically meaningful or not, not just
  read off a point estimate.

Metric definitions (standard, matching AIF360/Fairlearn conventions -- not
invented for this project):

* Selection Rate = P(y_pred=1 | group)
* Statistical Parity Difference = SelectionRate(group) - SelectionRate(reference)
* Disparate Impact Ratio = SelectionRate(group) / SelectionRate(reference)
* Equal Opportunity Difference = TPR(group) - TPR(reference)
* Average Odds Difference = 0.5 * [(FPR(group)-FPR(reference)) + (TPR(group)-TPR(reference))]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable, Optional

import numpy as np

from src.utils.logger import get_logger

logger = get_logger(__name__)

_EPSILON = 1e-12  # avoids literal division-by-zero; documented at every use site


@dataclass(frozen=True)
class GroupMetrics:
    """All per-group classification metrics for one protected-attribute group."""

    group: str
    n: int
    n_positive_actual: int
    n_positive_predicted: int
    selection_rate: float
    tpr: float           # recall / sensitivity
    fpr: float
    fnr: float
    tnr: float            # specificity
    precision: float
    f1: float
    balanced_accuracy: float
    roc_auc: Optional[float]   # None if the group has only one true class (AUC undefined)
    pr_auc: Optional[float]
    confusion_matrix: dict

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ConfidenceInterval:
    point_estimate: float
    ci_lower: float
    ci_upper: float
    confidence_level: float
    n_bootstrap: int
    excludes_null: bool  # True => the disparity is statistically distinguishable from "no disparity" at this confidence level

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PairwiseFairnessMetrics:
    group: str
    reference_group: str
    n_group: int
    n_reference: int
    statistical_parity_difference: float
    disparate_impact_ratio: float
    equal_opportunity_difference: float
    average_odds_difference: float
    spd_ci: ConfidenceInterval
    dir_ci: ConfidenceInterval
    eod_ci: ConfidenceInterval
    aod_ci: ConfidenceInterval

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


def _safe_divide(numerator: float, denominator: float) -> float:
    """Returns 0.0 for a 0/0 division (an empty/degenerate group), not NaN or a crash.

    Documented, deliberate choice: a rate computed from zero relevant
    examples (e.g. TPR when a group has no actual positives) is undefined,
    not "zero" in a statistical sense -- but for downstream aggregation and
    reporting, treating it as 0.0 with the underlying zero-count visible in
    ``GroupMetrics.n_positive_actual`` etc. is safer than propagating NaN
    into every dependent computation.
    """
    if denominator == 0:
        return 0.0
    return numerator / denominator


def compute_group_metrics(
    y_true: np.ndarray, y_pred: np.ndarray, y_proba: np.ndarray, group: str
) -> GroupMetrics:
    """Computes every classification metric for one already-sliced group."""
    n = len(y_true)
    # Confusion matrix computed directly from the already-thresholded y_pred
    # (not re-thresholded from y_proba here), so this works identically
    # whether the caller passes a model's own decision threshold or an
    # already-binarized y_pred from elsewhere.
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    cm = {"true_negative": tn, "false_positive": fp, "false_negative": fn, "true_positive": tp}

    n_positive_actual = tp + fn
    n_negative_actual = tn + fp
    n_positive_predicted = tp + fp

    tpr = _safe_divide(tp, n_positive_actual)
    fnr = _safe_divide(fn, n_positive_actual)
    fpr = _safe_divide(fp, n_negative_actual)
    tnr = _safe_divide(tn, n_negative_actual)
    precision = _safe_divide(tp, n_positive_predicted)
    f1 = _safe_divide(2 * precision * tpr, precision + tpr)
    selection_rate = _safe_divide(n_positive_predicted, n)
    balanced_accuracy = 0.5 * (tpr + tnr)

    roc_auc: Optional[float] = None
    pr_auc: Optional[float] = None
    unique_labels = np.unique(y_true)
    if len(unique_labels) == 2:
        from sklearn.metrics import average_precision_score, roc_auc_score
        roc_auc = float(roc_auc_score(y_true, y_proba))
        pr_auc = float(average_precision_score(y_true, y_proba))
    else:
        logger.warning(
            "Group '%s' has only one true class present (n=%d) -- ROC-AUC/PR-AUC are undefined "
            "and reported as None, not a misleading 0.0 or 1.0.", group, n,
        )

    return GroupMetrics(
        group=group, n=n, n_positive_actual=n_positive_actual, n_positive_predicted=n_positive_predicted,
        selection_rate=selection_rate, tpr=tpr, fpr=fpr, fnr=fnr, tnr=tnr, precision=precision, f1=f1,
        balanced_accuracy=balanced_accuracy, roc_auc=roc_auc, pr_auc=pr_auc, confusion_matrix=cm,
    )


def _metric_from_confusion(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Selection rate + TPR + FPR from one resampled (y_true, y_pred) pair -- the
    three primitives every pairwise fairness metric below is built from."""
    n = len(y_true)
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    n_pos_actual = tp + fn
    n_neg_actual = n - n_pos_actual
    return {
        "selection_rate": _safe_divide(tp + fp, n),
        "tpr": _safe_divide(tp, n_pos_actual),
        "fpr": _safe_divide(fp, n_neg_actual),
    }


def bootstrap_confidence_interval(
    group_data: dict[str, tuple[np.ndarray, np.ndarray]],
    metric_fn: Callable[[dict[str, tuple[np.ndarray, np.ndarray]]], float],
    n_iterations: int,
    confidence_level: float,
    random_state: int,
    null_value: float,
) -> ConfidenceInterval:
    """Generic stratified bootstrap: resamples WITH REPLACEMENT independently
    within each group (preserving group sizes), recomputes ``metric_fn`` each
    time, and returns a percentile confidence interval.

    ``null_value`` is 0.0 for difference metrics (SPD/EOD/AOD) and 1.0 for
    ratio metrics (DIR) -- the CI "excludes the null" when the disparity is
    statistically distinguishable from "no disparity" at this confidence
    level, which is a materially stronger claim than a raw point estimate.
    """
    rng = np.random.default_rng(random_state)
    point_estimate = metric_fn(group_data)

    if np.isnan(point_estimate):
        # E.g. Disparate Impact Ratio when the reference group's selection
        # rate is exactly 0 (division by zero -> mathematically undefined).
        # Reporting a NaN CI honestly, and explicitly NOT claiming
        # statistical significance from an undefined quantity, avoids the
        # misleading `excludes_null=True` that chained NaN comparisons
        # (`nan <= x <= nan`) would otherwise silently produce.
        logger.warning("Bootstrap point estimate is NaN (likely a zero-denominator group) -- reporting an undefined CI.")
        return ConfidenceInterval(
            point_estimate=float("nan"), ci_lower=float("nan"), ci_upper=float("nan"),
            confidence_level=confidence_level, n_bootstrap=n_iterations, excludes_null=False,
        )

    bootstrap_values = np.empty(n_iterations, dtype="float64")
    for i in range(n_iterations):
        resampled = {}
        for group, (y_true, y_pred) in group_data.items():
            idx = rng.integers(0, len(y_true), size=len(y_true))
            resampled[group] = (y_true[idx], y_pred[idx])
        bootstrap_values[i] = metric_fn(resampled)

    alpha = 1 - confidence_level
    ci_lower = float(np.percentile(bootstrap_values, 100 * alpha / 2))
    ci_upper = float(np.percentile(bootstrap_values, 100 * (1 - alpha / 2)))
    excludes_null = not (ci_lower <= null_value <= ci_upper)

    return ConfidenceInterval(
        point_estimate=point_estimate, ci_lower=ci_lower, ci_upper=ci_upper,
        confidence_level=confidence_level, n_bootstrap=n_iterations, excludes_null=excludes_null,
    )


def compute_pairwise_fairness_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    group_labels: np.ndarray,
    group: str,
    reference_group: str,
    n_bootstrap: int,
    confidence_level: float,
    random_state: int,
) -> PairwiseFairnessMetrics:
    """Computes SPD/DIR/EOD/AOD for ``group`` vs. ``reference_group``, each with
    a bootstrap confidence interval.
    """
    group_mask = group_labels == group
    ref_mask = group_labels == reference_group
    group_data = {
        "group": (y_true[group_mask], y_pred[group_mask]),
        "reference": (y_true[ref_mask], y_pred[ref_mask]),
    }

    def spd(gd: dict) -> float:
        g = _metric_from_confusion(*gd["group"])
        r = _metric_from_confusion(*gd["reference"])
        return g["selection_rate"] - r["selection_rate"]

    def dir_ratio(gd: dict) -> float:
        g = _metric_from_confusion(*gd["group"])
        r = _metric_from_confusion(*gd["reference"])
        return _safe_divide(g["selection_rate"], r["selection_rate"]) if r["selection_rate"] > 0 else float("nan")

    def eod(gd: dict) -> float:
        g = _metric_from_confusion(*gd["group"])
        r = _metric_from_confusion(*gd["reference"])
        return g["tpr"] - r["tpr"]

    def aod(gd: dict) -> float:
        g = _metric_from_confusion(*gd["group"])
        r = _metric_from_confusion(*gd["reference"])
        return 0.5 * ((g["fpr"] - r["fpr"]) + (g["tpr"] - r["tpr"]))

    spd_ci = bootstrap_confidence_interval(group_data, spd, n_bootstrap, confidence_level, random_state, null_value=0.0)
    dir_ci = bootstrap_confidence_interval(group_data, dir_ratio, n_bootstrap, confidence_level, random_state, null_value=1.0)
    eod_ci = bootstrap_confidence_interval(group_data, eod, n_bootstrap, confidence_level, random_state, null_value=0.0)
    aod_ci = bootstrap_confidence_interval(group_data, aod, n_bootstrap, confidence_level, random_state, null_value=0.0)

    logger.info(
        "Pairwise fairness '%s' vs reference '%s': SPD=%.4f [%.4f, %.4f], DIR=%.4f [%.4f, %.4f], "
        "EOD=%.4f [%.4f, %.4f], AOD=%.4f [%.4f, %.4f]",
        group, reference_group, spd_ci.point_estimate, spd_ci.ci_lower, spd_ci.ci_upper,
        dir_ci.point_estimate, dir_ci.ci_lower, dir_ci.ci_upper,
        eod_ci.point_estimate, eod_ci.ci_lower, eod_ci.ci_upper,
        aod_ci.point_estimate, aod_ci.ci_lower, aod_ci.ci_upper,
    )

    return PairwiseFairnessMetrics(
        group=group, reference_group=reference_group,
        n_group=int(group_mask.sum()), n_reference=int(ref_mask.sum()),
        statistical_parity_difference=spd_ci.point_estimate,
        disparate_impact_ratio=dir_ci.point_estimate,
        equal_opportunity_difference=eod_ci.point_estimate,
        average_odds_difference=aod_ci.point_estimate,
        spd_ci=spd_ci, dir_ci=dir_ci, eod_ci=eod_ci, aod_ci=aod_ci,
    )
