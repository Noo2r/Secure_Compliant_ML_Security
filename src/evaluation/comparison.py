"""Cross-model leaderboard construction and best-model selection.

Every candidate model is evaluated under identical CV fold boundaries and
the same final holdout (see :mod:`src.models.train`), which is what makes
this comparison fair rather than accidentally advantaging one model with
easier data splits.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

from src.models.train import ModelTrainingResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


def build_leaderboard(results: list[ModelTrainingResult]) -> pd.DataFrame:
    """One row per candidate model: CV + holdout metrics, cost, tuned params."""
    rows = []
    for r in results:
        rows.append({
            "model_name": r.model_name,
            "cv_pr_auc_mean": r.tuning_result.best_cv_score,
            "cv_pr_auc_std": float(np.std(r.tuning_result.cv_fold_scores)) if r.tuning_result.cv_fold_scores else np.nan,
            "holdout_pr_auc": r.holdout_metrics.pr_auc,
            "holdout_roc_auc": r.holdout_metrics.roc_auc,
            "holdout_f1": r.holdout_metrics.f1,
            "holdout_precision": r.holdout_metrics.precision,
            "holdout_recall": r.holdout_metrics.recall,
            "holdout_accuracy": r.holdout_metrics.accuracy,
            "decision_threshold": r.threshold_decision.threshold,
            "recall_at_precision_target": r.operational_metrics["recall_at_precision"]["recall"],
            "train_seconds": r.train_seconds,
            "n_optuna_trials": r.tuning_result.n_trials_completed,
            "best_params": r.tuning_result.best_params,
        })
    return pd.DataFrame(rows).sort_values("holdout_pr_auc", ascending=False).reset_index(drop=True)


@dataclass(frozen=True)
class BestModelSelection:
    model_name: str
    justification: str
    leaderboard_rank: int


def select_best_model(
    leaderboard: pd.DataFrame, tie_break_relative_tolerance: float = 0.01
) -> BestModelSelection:
    """Picks the winning model: highest holdout PR-AUC, with a documented tie-break.

    If the top model's PR-AUC is within ``tie_break_relative_tolerance``
    (relative) of any other model, the fastest-to-train of that near-tied
    group is preferred -- a defensible, auditable parsimony rule rather than
    silently taking whichever model happened to score a fraction of a
    percent higher.
    """
    ranked = leaderboard.sort_values("holdout_pr_auc", ascending=False).reset_index(drop=True)
    top_score = ranked.loc[0, "holdout_pr_auc"]
    near_tied = ranked[ranked["holdout_pr_auc"] >= top_score * (1 - tie_break_relative_tolerance)]

    if len(near_tied) > 1:
        winner_row = near_tied.sort_values("train_seconds").iloc[0]
        justification = (
            f"'{winner_row['model_name']}' is within {tie_break_relative_tolerance:.1%} PR-AUC of the top "
            f"score ({top_score:.4f}) among {len(near_tied)} near-tied models "
            f"({list(near_tied['model_name'])}); selected as the fastest to train "
            f"({winner_row['train_seconds']:.1f}s) among them."
        )
    else:
        winner_row = ranked.iloc[0]
        justification = (
            f"'{winner_row['model_name']}' has the highest holdout PR-AUC ({top_score:.4f}), "
            f"with no other model within {tie_break_relative_tolerance:.1%} relative tolerance."
        )

    rank = int(ranked[ranked["model_name"] == winner_row["model_name"]].index[0]) + 1
    selection = BestModelSelection(model_name=winner_row["model_name"], justification=justification, leaderboard_rank=rank)
    logger.info("Best model selected: %s", selection)
    return selection


def compare_top_models_statistically(
    results: list[ModelTrainingResult], model_a: str, model_b: str
) -> dict:
    """Wilcoxon signed-rank test on paired CV fold scores between two models.

    Answers whether model A's higher mean CV score is distinguishable from
    fold-to-fold noise, not just a bigger average -- a lightweight rigor
    check appropriate given both models were evaluated on identical folds
    (a paired comparison, which Wilcoxon is designed for).
    """
    result_a = next(r for r in results if r.model_name == model_a)
    result_b = next(r for r in results if r.model_name == model_b)
    scores_a = result_a.tuning_result.cv_fold_scores
    scores_b = result_b.tuning_result.cv_fold_scores

    if len(scores_a) != len(scores_b) or len(scores_a) < 3:
        return {
            "comparable": False,
            "reason": f"Need >=3 paired folds of equal length; got {len(scores_a)} vs {len(scores_b)}.",
        }

    statistic, p_value = wilcoxon(scores_a, scores_b)
    return {
        "comparable": True,
        "model_a": model_a,
        "model_b": model_b,
        "cv_scores_a": list(scores_a),
        "cv_scores_b": list(scores_b),
        "wilcoxon_statistic": float(statistic),
        "p_value": float(p_value),
        "significant_at_0.05": bool(p_value < 0.05),
    }
