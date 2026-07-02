"""Classification and fraud-operational evaluation metrics.

Two groups of metrics are provided, deliberately kept separate:

* **Standard classification metrics** (accuracy, precision, recall, F1,
  ROC/PR curves, confusion matrix, calibration) -- the metrics any
  classifier evaluation needs.
* **Operational fraud metrics** -- ``recall_at_precision``, ``precision_at_k``,
  and ``lift_and_gain``. PR-AUC alone tells you how good a ranking is in the
  abstract; it does not answer the question a fraud operations team actually
  asks: *"If we can only review the top 1,000 flagged transactions a day,
  what fraction are really fraud?"* (``precision_at_k``), *"If compliance
  requires 90% precision, how much fraud do we still catch?"*
  (``recall_at_precision``), or *"How much better than random screening is
  this model at each decile of risk?"* (``lift_and_gain``). All three are
  computed directly from ``(y_true, y_proba)`` with no dependency on model
  type, so they apply identically to every candidate algorithm.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


@dataclass(frozen=True)
class ClassificationMetrics:
    """Threshold-dependent + threshold-independent metrics for one model at one decision point."""

    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    pr_auc: float
    threshold: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


def compute_classification_metrics(
    y_true: np.ndarray, y_proba: np.ndarray, threshold: float
) -> ClassificationMetrics:
    """Computes the standard metric set at a given decision threshold.

    ``roc_auc``/``pr_auc`` are threshold-independent (computed from
    ``y_proba`` directly); the rest are evaluated at ``threshold``.
    """
    y_pred = (y_proba >= threshold).astype(int)
    return ClassificationMetrics(
        accuracy=float(accuracy_score(y_true, y_pred)),
        precision=float(precision_score(y_true, y_pred, zero_division=0)),
        recall=float(recall_score(y_true, y_pred, zero_division=0)),
        f1=float(f1_score(y_true, y_pred, zero_division=0)),
        roc_auc=float(roc_auc_score(y_true, y_proba)),
        pr_auc=float(average_precision_score(y_true, y_proba)),
        threshold=float(threshold),
    )


def compute_confusion_matrix(y_true: np.ndarray, y_proba: np.ndarray, threshold: float) -> dict[str, int]:
    """Returns the confusion matrix at ``threshold`` as a labeled dict (tn/fp/fn/tp)."""
    y_pred = (y_proba >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {"true_negative": int(tn), "false_positive": int(fp), "false_negative": int(fn), "true_positive": int(tp)}


def compute_roc_curve(y_true: np.ndarray, y_proba: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    fpr, tpr, thresholds = roc_curve(y_true, y_proba)
    return fpr, tpr, thresholds


def compute_pr_curve(y_true: np.ndarray, y_proba: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    precision, recall, thresholds = precision_recall_curve(y_true, y_proba)
    return precision, recall, thresholds


def compute_calibration_curve(
    y_true: np.ndarray, y_proba: np.ndarray, n_bins: int = 10
) -> tuple[np.ndarray, np.ndarray]:
    """Returns (mean predicted probability, observed fraud rate) per bin."""
    prob_true, prob_pred = calibration_curve(y_true, y_proba, n_bins=n_bins, strategy="quantile")
    return prob_true, prob_pred


# ----------------------------------------------------------------------
# Operational fraud metrics
# ----------------------------------------------------------------------

def recall_at_precision(
    y_true: np.ndarray, y_proba: np.ndarray, min_precision: float
) -> dict[str, float]:
    """Highest recall achievable while precision stays at or above ``min_precision``.

    Answers: "If compliance requires at least X% precision, how much fraud
    do we still catch?" Walks the precision-recall curve (already sorted by
    threshold) and picks the highest-recall point meeting the precision
    floor. Returns the floor-precision itself if no threshold reaches it,
    with ``achieved`` set to ``False`` so callers can distinguish "met the
    bar" from "best available fallback".
    """
    precision, recall, thresholds = precision_recall_curve(y_true, y_proba)
    # precision_recall_curve returns arrays 1 longer than thresholds (last
    # point has no corresponding threshold); align by dropping the last entry.
    precision, recall = precision[:-1], recall[:-1]
    meets_floor = precision >= min_precision
    if not meets_floor.any():
        best_idx = int(np.argmax(precision))
        return {
            "min_precision_target": float(min_precision),
            "achieved_precision": float(precision[best_idx]),
            "recall": float(recall[best_idx]),
            "threshold": float(thresholds[best_idx]),
            "target_met": False,
        }
    candidate_recalls = np.where(meets_floor, recall, -np.inf)
    best_idx = int(np.argmax(candidate_recalls))
    return {
        "min_precision_target": float(min_precision),
        "achieved_precision": float(precision[best_idx]),
        "recall": float(recall[best_idx]),
        "threshold": float(thresholds[best_idx]),
        "target_met": True,
    }


def precision_at_k(y_true: np.ndarray, y_proba: np.ndarray, k: int) -> dict[str, float]:
    """Precision among the top-``k`` highest-scored transactions.

    Answers: "If the fraud review team can only investigate the top K
    flagged transactions, what fraction are actually fraud?" A direct,
    threshold-free proxy for a fixed daily review capacity.
    """
    k = min(k, len(y_true))
    order = np.argsort(-y_proba)
    top_k_labels = np.asarray(y_true)[order[:k]]
    precision = float(top_k_labels.sum() / k) if k > 0 else 0.0
    return {"k": int(k), "precision_at_k": precision, "frauds_captured": int(top_k_labels.sum())}


def lift_and_gain(y_true: np.ndarray, y_proba: np.ndarray, n_bins: int = 10) -> pd.DataFrame:
    """Decile-based lift/gain table.

    Sorts transactions by descending predicted fraud probability, splits
    them into ``n_bins`` equal-sized groups (decile 1 = highest risk), and
    for each cumulative group reports the fraction of all fraud captured
    (gain) and the ratio of that capture rate to random screening (lift).
    A lift of e.g. 8.0 at decile 1 means: screening only the top 10% of
    transactions by model score catches 8x as much fraud as screening a
    random 10% would.
    """
    n = len(y_true)
    base_rate = float(np.asarray(y_true).mean())
    order = np.argsort(-y_proba)
    sorted_labels = np.asarray(y_true)[order]

    rows = []
    total_frauds = sorted_labels.sum()
    bin_size = max(1, n // n_bins)
    for decile in range(1, n_bins + 1):
        cutoff = min(decile * bin_size, n)
        cumulative_labels = sorted_labels[:cutoff]
        cumulative_fraud_count = int(cumulative_labels.sum())
        cumulative_fraud_rate = cumulative_fraud_count / cutoff if cutoff > 0 else 0.0
        gain = cumulative_fraud_count / total_frauds if total_frauds > 0 else 0.0
        lift = cumulative_fraud_rate / base_rate if base_rate > 0 else 0.0
        rows.append({
            "decile": decile,
            "cumulative_pct_of_population": cutoff / n,
            "cumulative_frauds_captured": cumulative_fraud_count,
            "gain": gain,
            "lift": lift,
        })
    return pd.DataFrame(rows)
