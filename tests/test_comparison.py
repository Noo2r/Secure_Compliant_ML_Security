from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.evaluation.comparison import build_leaderboard, compare_top_models_statistically, select_best_model


def _fake_result(name: str, holdout_pr_auc: float, train_seconds: float, cv_scores):
    result = MagicMock()
    result.model_name = name
    result.tuning_result.best_cv_score = holdout_pr_auc
    result.tuning_result.cv_fold_scores = cv_scores
    result.tuning_result.best_params = {"dummy": 1}
    result.tuning_result.n_trials_completed = 5
    result.holdout_metrics.pr_auc = holdout_pr_auc
    result.holdout_metrics.roc_auc = holdout_pr_auc + 0.05
    result.holdout_metrics.f1 = holdout_pr_auc - 0.1
    result.holdout_metrics.precision = holdout_pr_auc
    result.holdout_metrics.recall = holdout_pr_auc
    result.holdout_metrics.accuracy = 0.95
    result.threshold_decision.threshold = 0.5
    result.operational_metrics = {
        "recall_at_precision": {"recall": 0.5, "achieved_precision": 0.9, "min_precision_target": 0.9, "target_met": True},
        "precision_at_k": [{"k": 100, "precision_at_k": 0.8, "frauds_captured": 80}],
        "lift_and_gain": pd.DataFrame({"decile": [1], "lift": [5.0], "gain": [0.5], "cumulative_pct_of_population": [0.1]}),
    }
    result.train_seconds = train_seconds
    return result


def test_build_leaderboard_sorted_by_holdout_pr_auc() -> None:
    results = [
        _fake_result("model_a", 0.5, 10.0, [0.48, 0.50, 0.52]),
        _fake_result("model_b", 0.7, 20.0, [0.68, 0.70, 0.72]),
    ]
    leaderboard = build_leaderboard(results)
    assert leaderboard.iloc[0]["model_name"] == "model_b"
    assert leaderboard.iloc[1]["model_name"] == "model_a"


def test_select_best_model_picks_top_score_when_no_tie() -> None:
    results = [
        _fake_result("model_a", 0.5, 10.0, [0.48, 0.50, 0.52]),
        _fake_result("model_b", 0.7, 20.0, [0.68, 0.70, 0.72]),
    ]
    leaderboard = build_leaderboard(results)
    selection = select_best_model(leaderboard, tie_break_relative_tolerance=0.01)
    assert selection.model_name == "model_b"
    assert selection.leaderboard_rank == 1


def test_select_best_model_prefers_faster_model_when_near_tied() -> None:
    results = [
        _fake_result("slow_model", 0.700, 100.0, [0.69, 0.70, 0.71]),
        _fake_result("fast_model", 0.699, 5.0, [0.68, 0.70, 0.72]),  # within 1% relative of top score
    ]
    leaderboard = build_leaderboard(results)
    selection = select_best_model(leaderboard, tie_break_relative_tolerance=0.01)
    assert selection.model_name == "fast_model"
    assert "fastest to train" in selection.justification


def test_compare_top_models_statistically_requires_equal_fold_counts() -> None:
    results = [
        _fake_result("model_a", 0.5, 10.0, [0.48, 0.50, 0.52]),
        _fake_result("model_b", 0.7, 20.0, [0.68, 0.70]),  # different fold count
    ]
    comparison = compare_top_models_statistically(results, "model_a", "model_b")
    assert comparison["comparable"] is False


def test_compare_top_models_statistically_runs_wilcoxon() -> None:
    results = [
        _fake_result("model_a", 0.5, 10.0, [0.40, 0.45, 0.42, 0.48]),
        _fake_result("model_b", 0.7, 20.0, [0.68, 0.70, 0.72, 0.71]),
    ]
    comparison = compare_top_models_statistically(results, "model_a", "model_b")
    assert comparison["comparable"] is True
    assert "p_value" in comparison
