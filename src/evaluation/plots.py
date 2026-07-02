"""Evaluation plot generation (ROC, PR, confusion matrix, calibration,
learning/validation curves, feature importance, lift/gain) saved as PNGs.

Kept as plain functions taking already-computed arrays/DataFrames (from
:mod:`src.evaluation.metrics` / :mod:`src.models.train`) rather than
recomputing anything, so plotting never silently diverges from the logged
metrics.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless: this pipeline runs as a script/CI job, never an interactive session
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", dpi=120)
    plt.close(fig)


def plot_roc_curve(fpr: np.ndarray, tpr: np.ndarray, roc_auc: float, model_name: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr, label=f"{model_name} (AUC={roc_auc:.3f})")
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Random")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title(f"ROC Curve — {model_name}")
    ax.legend()
    _save(fig, path)


def plot_pr_curve(precision: np.ndarray, recall: np.ndarray, pr_auc: float, model_name: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(recall, precision, label=f"{model_name} (PR-AUC={pr_auc:.3f})")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title(f"Precision-Recall Curve — {model_name}")
    ax.legend()
    _save(fig, path)


def plot_confusion_matrix(confusion: dict[str, int], model_name: str, path: Path) -> None:
    matrix = np.array([
        [confusion["true_negative"], confusion["false_positive"]],
        [confusion["false_negative"], confusion["true_positive"]],
    ])
    fig, ax = plt.subplots(figsize=(5, 4.5))
    im = ax.imshow(matrix, cmap="Blues")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"{matrix[i, j]:,}", ha="center", va="center")
    ax.set_xticks([0, 1], labels=["Pred: Not Fraud", "Pred: Fraud"])
    ax.set_yticks([0, 1], labels=["True: Not Fraud", "True: Fraud"])
    ax.set_title(f"Confusion Matrix — {model_name}")
    fig.colorbar(im)
    _save(fig, path)


def plot_calibration_curve(prob_true: np.ndarray, prob_pred: np.ndarray, model_name: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(prob_pred, prob_true, marker="o", label=model_name)
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Perfectly calibrated")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Observed fraud rate")
    ax.set_title(f"Calibration Curve — {model_name}")
    ax.legend()
    _save(fig, path)


def plot_learning_curve(curve_df: pd.DataFrame, model_name: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(curve_df["train_rows"], curve_df["train_pr_auc"], marker="o", label="Train PR-AUC")
    ax.plot(curve_df["train_rows"], curve_df["validation_pr_auc"], marker="o", label="Validation PR-AUC")
    ax.set_xlabel("Training rows")
    ax.set_ylabel("PR-AUC")
    ax.set_title(f"Learning Curve — {model_name}")
    ax.legend()
    _save(fig, path)


def plot_validation_curve(curve_df: pd.DataFrame, param_name: str, model_name: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(curve_df[param_name], curve_df["train_pr_auc"], marker="o", label="Train PR-AUC")
    ax.plot(curve_df[param_name], curve_df["validation_pr_auc"], marker="o", label="Validation PR-AUC")
    ax.set_xlabel(param_name)
    ax.set_ylabel("PR-AUC")
    ax.set_title(f"Validation Curve ({param_name}) — {model_name}")
    ax.legend()
    _save(fig, path)


def plot_feature_importance(importance: pd.Series, model_name: str, path: Path, top_n: int = 25) -> None:
    top = importance.head(top_n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7, max(4, top_n * 0.25)))
    ax.barh(top.index, top.values)
    ax.set_xlabel("Importance")
    ax.set_title(f"Top {top_n} Feature Importances — {model_name}")
    _save(fig, path)


def plot_lift_gain(lift_gain_df: pd.DataFrame, model_name: str, path: Path) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    ax1.plot(lift_gain_df["decile"], lift_gain_df["lift"], marker="o")
    ax1.axhline(1.0, linestyle="--", color="gray", label="Random screening")
    ax1.set_xlabel("Decile (1 = highest risk)")
    ax1.set_ylabel("Lift")
    ax1.set_title(f"Lift Chart — {model_name}")
    ax1.legend()

    ax2.plot(lift_gain_df["cumulative_pct_of_population"], lift_gain_df["gain"], marker="o", label=model_name)
    ax2.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Random screening")
    ax2.set_xlabel("Cumulative % of population reviewed")
    ax2.set_ylabel("Cumulative % of fraud captured")
    ax2.set_title(f"Gain Chart — {model_name}")
    ax2.legend()
    _save(fig, path)
