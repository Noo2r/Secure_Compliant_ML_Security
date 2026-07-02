"""DP-specific plots: training curves (Normal vs DP loss/metric per epoch)
and the privacy-utility tradeoff curve (epsilon vs. utility across a noise
multiplier sweep).

ROC and PR comparison plots are NOT reimplemented here -- Module 3's
``src.evaluation.plots.plot_roc_curve``/``plot_pr_curve`` are reused directly
by ``scripts/run_module4.py`` (called once per variant), since those
functions are already fully generic and need no DP-specific behavior.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", dpi=120)
    plt.close(fig)


def plot_training_curves(
    normal_history: dict[str, list[float]],
    dp_history: dict[str, list[float]],
    metric_key: str,
    path: Path,
) -> None:
    """Overlays Normal vs. DP training curves for one Keras history metric key."""
    fig, ax = plt.subplots(figsize=(7, 5))
    if metric_key in normal_history:
        ax.plot(range(1, len(normal_history[metric_key]) + 1), normal_history[metric_key],
                 marker="o", label=f"Normal NN ({metric_key})")
    if metric_key in dp_history:
        ax.plot(range(1, len(dp_history[metric_key]) + 1), dp_history[metric_key],
                 marker="o", label=f"DP NN ({metric_key})")
    ax.set_xlabel("Epoch")
    ax.set_ylabel(metric_key)
    ax.set_title(f"Training Curve — Normal vs. DP ({metric_key})")
    ax.legend()
    _save(fig, path)


def plot_privacy_utility_curve(sweep_df: pd.DataFrame, primary_metric: str, path: Path) -> None:
    """Plots utility (e.g. PR-AUC) against epsilon across a noise-multiplier sweep.

    ``sweep_df`` must have columns ``noise_multiplier``, ``epsilon``, and
    ``primary_metric``, one row per sweep point (see
    :func:`src.privacy.dp_model` sweep orchestration in
    ``scripts/run_module4.py``).
    """
    ordered = sweep_df.sort_values("epsilon")
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(ordered["epsilon"], ordered[primary_metric], marker="o")
    for _, row in ordered.iterrows():
        ax.annotate(f"σ={row['noise_multiplier']:.2g}", (row["epsilon"], row[primary_metric]),
                    textcoords="offset points", xytext=(5, 5), fontsize=8)
    ax.set_xlabel("Privacy budget (epsilon) — lower is more private")
    ax.set_ylabel(primary_metric.upper())
    ax.set_title("Privacy-Utility Tradeoff")
    _save(fig, path)
