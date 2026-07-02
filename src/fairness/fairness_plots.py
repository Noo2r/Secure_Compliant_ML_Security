"""Fairness visualization generation -- bar charts, disparate impact plots,
per-group confusion matrices/ROC/PR curves, and a combined dashboard.

Mirrors :mod:`src.evaluation.plots`'s conventions (headless Agg backend,
one function per chart, save-to-path, no return value) rather than
reimplementing the plotting style from scratch.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from src.fairness.fairness_metrics import GroupMetrics, PairwiseFairnessMetrics
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _save(fig: plt.Figure, path: Path, dpi: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", dpi=dpi)
    plt.close(fig)


def plot_selection_rate_comparison(group_metrics: dict[str, GroupMetrics], attribute: str, path: Path, dpi: int) -> None:
    groups = list(group_metrics.keys())
    rates = [group_metrics[g].selection_rate for g in groups]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(groups, rates, color="#4C72B0")
    ax.set_ylabel("Selection Rate (P(predicted fraud))")
    ax.set_title(f"Selection Rate by {attribute}")
    for i, r in enumerate(rates):
        ax.text(i, r, f"{r:.4f}", ha="center", va="bottom")
    _save(fig, path, dpi)


def plot_error_rate_comparison(group_metrics: dict[str, GroupMetrics], attribute: str, path: Path, dpi: int) -> None:
    groups = list(group_metrics.keys())
    fpr = [group_metrics[g].fpr for g in groups]
    fnr = [group_metrics[g].fnr for g in groups]
    x = np.arange(len(groups))
    width = 0.35
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(x - width / 2, fpr, width, label="False Positive Rate", color="#DD8452")
    ax.bar(x + width / 2, fnr, width, label="False Negative Rate", color="#C44E52")
    ax.set_xticks(x, groups)
    ax.set_ylabel("Rate")
    ax.set_title(f"Error Rates by {attribute}")
    ax.legend()
    _save(fig, path, dpi)


def plot_fairness_metric_bars(pairwise_metrics: dict[str, PairwiseFairnessMetrics], attribute: str, path: Path, dpi: int) -> None:
    """Bar chart of SPD/EOD/AOD per group, with 95% bootstrap CI error bars."""
    groups = list(pairwise_metrics.keys())
    spd = [pairwise_metrics[g].spd_ci.point_estimate for g in groups]
    spd_err = [
        [pairwise_metrics[g].spd_ci.point_estimate - pairwise_metrics[g].spd_ci.ci_lower for g in groups],
        [pairwise_metrics[g].spd_ci.ci_upper - pairwise_metrics[g].spd_ci.point_estimate for g in groups],
    ]
    eod = [pairwise_metrics[g].eod_ci.point_estimate for g in groups]
    eod_err = [
        [pairwise_metrics[g].eod_ci.point_estimate - pairwise_metrics[g].eod_ci.ci_lower for g in groups],
        [pairwise_metrics[g].eod_ci.ci_upper - pairwise_metrics[g].eod_ci.point_estimate for g in groups],
    ]
    aod = [pairwise_metrics[g].aod_ci.point_estimate for g in groups]
    aod_err = [
        [pairwise_metrics[g].aod_ci.point_estimate - pairwise_metrics[g].aod_ci.ci_lower for g in groups],
        [pairwise_metrics[g].aod_ci.ci_upper - pairwise_metrics[g].aod_ci.point_estimate for g in groups],
    ]

    x = np.arange(len(groups))
    width = 0.25
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - width, spd, width, yerr=spd_err, capsize=4, label="Statistical Parity Diff.", color="#4C72B0")
    ax.bar(x, eod, width, yerr=eod_err, capsize=4, label="Equal Opportunity Diff.", color="#55A868")
    ax.bar(x + width, aod, width, yerr=aod_err, capsize=4, label="Average Odds Diff.", color="#8172B2")
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.set_xticks(x, groups)
    ax.set_ylabel("Difference (vs. reference group)")
    ax.set_title(f"Fairness Metrics with 95% Bootstrap CI — {attribute}")
    ax.legend()
    _save(fig, path, dpi)


def plot_disparate_impact(pairwise_metrics: dict[str, PairwiseFairnessMetrics], attribute: str,
                           di_low: float, di_high: float, path: Path, dpi: int) -> None:
    groups = list(pairwise_metrics.keys())
    dir_values = [pairwise_metrics[g].dir_ci.point_estimate for g in groups]
    err = [
        [pairwise_metrics[g].dir_ci.point_estimate - pairwise_metrics[g].dir_ci.ci_lower for g in groups],
        [pairwise_metrics[g].dir_ci.ci_upper - pairwise_metrics[g].dir_ci.point_estimate for g in groups],
    ]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(groups, dir_values, yerr=err, capsize=4, color="#4C72B0")
    ax.axhline(1.0, color="black", linewidth=0.8, label="Perfect parity")
    ax.axhspan(di_low, di_high, color="green", alpha=0.1, label=f"Four-fifths rule band [{di_low}, {di_high}]")
    ax.set_ylabel("Disparate Impact Ratio")
    ax.set_title(f"Disparate Impact Ratio — {attribute}")
    ax.legend()
    _save(fig, path, dpi)


def plot_group_confusion_matrices(group_metrics: dict[str, GroupMetrics], attribute: str, path: Path, dpi: int) -> None:
    groups = list(group_metrics.keys())
    n = len(groups)
    fig, axes = plt.subplots(1, n, figsize=(4.5 * n, 4))
    if n == 1:
        axes = [axes]
    for ax, g in zip(axes, groups):
        cm = group_metrics[g].confusion_matrix
        matrix = np.array([[cm["true_negative"], cm["false_positive"]], [cm["false_negative"], cm["true_positive"]]])
        im = ax.imshow(matrix, cmap="Blues")
        for i in range(2):
            for j in range(2):
                ax.text(j, i, f"{matrix[i, j]:,}", ha="center", va="center")
        ax.set_xticks([0, 1], labels=["Pred: Not Fraud", "Pred: Fraud"])
        ax.set_yticks([0, 1], labels=["True: Not Fraud", "True: Fraud"])
        ax.set_title(g)
    fig.suptitle(f"Confusion Matrix by {attribute}")
    _save(fig, path, dpi)


def plot_roc_per_group(y_true_by_group: dict[str, np.ndarray], y_proba_by_group: dict[str, np.ndarray],
                        attribute: str, path: Path, dpi: int) -> None:
    from sklearn.metrics import roc_auc_score, roc_curve
    fig, ax = plt.subplots(figsize=(6, 5))
    for g, y_true in y_true_by_group.items():
        if len(np.unique(y_true)) < 2:
            logger.warning("Skipping ROC curve for group '%s' (%s): only one class present.", g, attribute)
            continue
        fpr, tpr, _ = roc_curve(y_true, y_proba_by_group[g])
        auc = roc_auc_score(y_true, y_proba_by_group[g])
        ax.plot(fpr, tpr, label=f"{g} (AUC={auc:.3f})")
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title(f"ROC Curve by {attribute}")
    ax.legend()
    _save(fig, path, dpi)


def plot_pr_per_group(y_true_by_group: dict[str, np.ndarray], y_proba_by_group: dict[str, np.ndarray],
                       attribute: str, path: Path, dpi: int) -> None:
    from sklearn.metrics import average_precision_score, precision_recall_curve
    fig, ax = plt.subplots(figsize=(6, 5))
    for g, y_true in y_true_by_group.items():
        if len(np.unique(y_true)) < 2:
            logger.warning("Skipping PR curve for group '%s' (%s): only one class present.", g, attribute)
            continue
        precision, recall, _ = precision_recall_curve(y_true, y_proba_by_group[g])
        ap = average_precision_score(y_true, y_proba_by_group[g])
        ax.plot(recall, precision, label=f"{g} (PR-AUC={ap:.3f})")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title(f"Precision-Recall Curve by {attribute}")
    ax.legend()
    _save(fig, path, dpi)


def plot_fairness_dashboard(
    group_metrics: dict[str, GroupMetrics], pairwise_metrics: dict[str, PairwiseFairnessMetrics],
    attribute: str, path: Path, dpi: int,
) -> None:
    """A single combined figure: selection rate, error rates, SPD/EOD/AOD
    with CIs, and disparate impact ratio -- the "one-glance" fairness view."""
    groups = list(group_metrics.keys())
    fig, axes = plt.subplots(2, 2, figsize=(13, 10))

    axes[0, 0].bar(groups, [group_metrics[g].selection_rate for g in groups], color="#4C72B0")
    axes[0, 0].set_title("Selection Rate")

    x = np.arange(len(groups))
    width = 0.35
    axes[0, 1].bar(x - width / 2, [group_metrics[g].fpr for g in groups], width, label="FPR", color="#DD8452")
    axes[0, 1].bar(x + width / 2, [group_metrics[g].fnr for g in groups], width, label="FNR", color="#C44E52")
    axes[0, 1].set_xticks(x, groups)
    axes[0, 1].set_title("Error Rates")
    axes[0, 1].legend()

    if pairwise_metrics:
        pg = list(pairwise_metrics.keys())
        axes[1, 0].bar(pg, [pairwise_metrics[g].statistical_parity_difference for g in pg], color="#55A868")
        axes[1, 0].axhline(0.0, color="black", linewidth=0.8)
        axes[1, 0].set_title("Statistical Parity Difference (vs. reference)")

        axes[1, 1].bar(pg, [pairwise_metrics[g].disparate_impact_ratio for g in pg], color="#8172B2")
        axes[1, 1].axhline(1.0, color="black", linewidth=0.8)
        axes[1, 1].set_title("Disparate Impact Ratio (vs. reference)")
    else:
        for ax in (axes[1, 0], axes[1, 1]):
            ax.text(0.5, 0.5, "No reference group comparison\n(single-group attribute)", ha="center", va="center")

    fig.suptitle(f"Fairness Dashboard — {attribute}", fontsize=14)
    _save(fig, path, dpi)
