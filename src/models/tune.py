"""Optuna-based hyperparameter tuning with time-aware cross-validation.

Uses ``TimeSeriesSplit`` (walk-forward folds), not random/stratified k-fold,
for the same reason Module 2 used a chronological train/test split: a fraud
model only ever scores transactions that happen after the ones it trained
on, so a validation fold must always follow its training fold in time or
the CV score is optimistically biased. The exact same fold boundaries are
reused across every candidate model so the comparison in Module 3's
leaderboard is fair -- no model gets easier folds than another.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
import optuna
from sklearn.metrics import average_precision_score
from sklearn.model_selection import TimeSeriesSplit

from src.models.model_registry import ModelSpec, compute_scale_pos_weight
from src.utils.logger import get_logger

logger = get_logger(__name__)

optuna.logging.set_verbosity(optuna.logging.WARNING)


@dataclass(frozen=True)
class TuningResult:
    model_name: str
    best_params: dict
    best_cv_score: float
    cv_fold_scores: tuple[float, ...]
    n_trials_completed: int
    tuning_seconds: float


def sample_time_ordered(X: np.ndarray, y: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Deterministic, evenly-spaced systematic sample that preserves time order.

    Used to keep expensive hyperparameter search tractable (mirrors Module
    2's ``ranking_sample_size`` precedent) while still spanning the entire
    training time range -- an evenly-spaced sample, not just the most recent
    rows, so seasonal/day-of-week patterns across the full period remain
    represented in the tuning sample.
    """
    if n >= len(X):
        return X, y
    indices = np.linspace(0, len(X) - 1, n).astype(int)
    return X[indices], y[indices]


class HyperparameterTuner:
    """Runs an Optuna study for one model, scored by time-aware CV PR-AUC."""

    def __init__(
        self,
        model_spec: ModelSpec,
        cv_folds: int,
        n_trials: int,
        timeout_seconds: int,
        random_state: int = 42,
    ) -> None:
        self.model_spec = model_spec
        self.cv_folds = cv_folds
        self.n_trials = n_trials
        self.timeout_seconds = timeout_seconds
        self.random_state = random_state

    def tune(self, X: np.ndarray, y: np.ndarray) -> TuningResult:
        splitter = TimeSeriesSplit(n_splits=self.cv_folds)
        scale_pos_weight = compute_scale_pos_weight(y)
        start_time = time.monotonic()

        def objective(trial: optuna.Trial) -> float:
            params = self.model_spec.suggest_params(trial)
            fold_scores = []
            for train_idx, val_idx in splitter.split(X):
                estimator = self.model_spec.build_estimator(params, scale_pos_weight, self.random_state)
                estimator.fit(X[train_idx], y[train_idx])
                y_proba = estimator.predict_proba(X[val_idx])[:, 1]
                fold_scores.append(average_precision_score(y[val_idx], y_proba))
            trial.set_user_attr("fold_scores", fold_scores)
            return float(np.mean(fold_scores))

        study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=self.random_state))
        logger.info(
            "Starting Optuna tuning for '%s': %d trials, timeout=%ds, cv_folds=%d",
            self.model_spec.name, self.n_trials, self.timeout_seconds, self.cv_folds,
        )
        study.optimize(objective, n_trials=self.n_trials, timeout=self.timeout_seconds, show_progress_bar=False)

        elapsed = time.monotonic() - start_time
        best_fold_scores = tuple(study.best_trial.user_attrs.get("fold_scores", []))
        result = TuningResult(
            model_name=self.model_spec.name,
            best_params=study.best_params,
            best_cv_score=float(study.best_value),
            cv_fold_scores=best_fold_scores,
            n_trials_completed=len(study.trials),
            tuning_seconds=elapsed,
        )
        logger.info(
            "Tuning complete for '%s': best CV PR-AUC=%.4f over %d trials in %.1fs",
            self.model_spec.name, result.best_cv_score, result.n_trials_completed, elapsed,
        )
        return result
