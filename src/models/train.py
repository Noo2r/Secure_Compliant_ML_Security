"""Per-model training orchestration: tune -> refit -> threshold -> evaluate.

Uses a three-way time-ordered split of the data Module 2 already produced:

    Module 2 train.csv  =>  [ train_core (~85%) | threshold_val (~15%) ]
    Module 2 test.csv   =>  final holdout (touched once, for the leaderboard
                             and once more for the winning model's full
                             evaluation suite)

``train_core`` is what the final estimator is actually fit on;
``threshold_val`` -- a genuinely unseen, chronologically later slice -- is
what the decision threshold is calibrated on. This is a deliberate,
documented trade-off (the final model sees slightly less than 100% of the
Module 2 training data) in exchange for a threshold estimate that isn't
contaminated by evaluating on data the model was fit on.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
import pandas as pd

from src.evaluation.metrics import (
    ClassificationMetrics,
    compute_calibration_curve,
    compute_classification_metrics,
    compute_confusion_matrix,
    compute_pr_curve,
    compute_roc_curve,
    lift_and_gain,
    precision_at_k,
    recall_at_precision,
)
from src.models.model_registry import ModelSpec, compute_scale_pos_weight
from src.models.threshold import ThresholdDecision, optimize_threshold
from src.models.tune import HyperparameterTuner, TuningResult, sample_time_ordered
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ModelTrainingResult:
    model_name: str
    tuning_result: TuningResult
    fitted_estimator: Any
    threshold_decision: ThresholdDecision
    holdout_metrics: ClassificationMetrics
    holdout_confusion_matrix: dict
    holdout_roc_curve: tuple
    holdout_pr_curve: tuple
    holdout_calibration_curve: tuple
    operational_metrics: dict
    feature_importance: Optional[pd.Series]
    train_seconds: float
    scale_pos_weight: float


def _time_ordered_train_val_split(
    X: np.ndarray, y: np.ndarray, validation_fraction: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    split_idx = int(len(X) * (1 - validation_fraction))
    return X[:split_idx], y[:split_idx], X[split_idx:], y[split_idx:]


def _extract_feature_importance(estimator: Any, feature_names: list[str]) -> Optional[pd.Series]:
    if hasattr(estimator, "feature_importances_"):
        return pd.Series(estimator.feature_importances_, index=feature_names).sort_values(ascending=False)
    if hasattr(estimator, "coef_"):
        coefs = np.ravel(estimator.coef_)
        return pd.Series(np.abs(coefs), index=feature_names).sort_values(ascending=False)
    return None  # e.g. the Keras NN wrapper -- covered by SHAP in a later module instead


class ModelTrainer:
    """Tunes, refits, calibrates a threshold for, and evaluates one candidate model."""

    def __init__(
        self,
        model_spec: ModelSpec,
        cv_folds: int,
        n_trials: int,
        timeout_seconds: int,
        tuning_sample_size: int,
        threshold_strategy: str,
        threshold_min_precision: float,
        validation_fraction_of_train: float,
        precision_threshold: float,
        top_k_values: tuple[int, ...],
        random_state: int = 42,
    ) -> None:
        self.model_spec = model_spec
        self.cv_folds = cv_folds
        self.n_trials = n_trials
        self.timeout_seconds = timeout_seconds
        self.tuning_sample_size = tuning_sample_size
        self.threshold_strategy = threshold_strategy
        self.threshold_min_precision = threshold_min_precision
        self.validation_fraction_of_train = validation_fraction_of_train
        self.precision_threshold = precision_threshold
        self.top_k_values = top_k_values
        self.random_state = random_state

    def train_and_evaluate(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
        feature_names: list[str],
    ) -> ModelTrainingResult:
        start_time = time.monotonic()

        # --- Hyperparameter tuning on a time-ordered sample of train_core ---
        train_core_X, train_core_y, val_X, val_y = _time_ordered_train_val_split(
            X_train, y_train, self.validation_fraction_of_train
        )
        tuning_X, tuning_y = sample_time_ordered(train_core_X, train_core_y, self.tuning_sample_size)
        tuner = HyperparameterTuner(
            self.model_spec, self.cv_folds, self.n_trials, self.timeout_seconds, self.random_state
        )
        tuning_result = tuner.tune(tuning_X, tuning_y)

        # --- Refit on the full train_core with the best hyperparameters ---
        scale_pos_weight = compute_scale_pos_weight(train_core_y)
        estimator = self.model_spec.build_estimator(tuning_result.best_params, scale_pos_weight, self.random_state)
        estimator.fit(train_core_X, train_core_y)

        # --- Threshold calibration on the untouched, chronologically-later val slice ---
        val_proba = estimator.predict_proba(val_X)[:, 1]
        threshold_decision = optimize_threshold(
            val_y, val_proba, self.threshold_strategy, self.threshold_min_precision
        )

        # --- Single-touch evaluation on the Module 2 test holdout ---
        test_proba = estimator.predict_proba(X_test)[:, 1]
        holdout_metrics = compute_classification_metrics(y_test, test_proba, threshold_decision.threshold)
        holdout_confusion = compute_confusion_matrix(y_test, test_proba, threshold_decision.threshold)
        holdout_roc = compute_roc_curve(y_test, test_proba)
        holdout_pr = compute_pr_curve(y_test, test_proba)
        holdout_calibration = compute_calibration_curve(y_test, test_proba)

        operational_metrics = {
            "recall_at_precision": recall_at_precision(y_test, test_proba, self.precision_threshold),
            "precision_at_k": [precision_at_k(y_test, test_proba, k) for k in self.top_k_values],
            "lift_and_gain": lift_and_gain(y_test, test_proba),
        }

        feature_importance = _extract_feature_importance(estimator, feature_names)
        elapsed = time.monotonic() - start_time

        logger.info(
            "'%s' trained+evaluated in %.1fs: holdout PR-AUC=%.4f, ROC-AUC=%.4f, F1=%.4f",
            self.model_spec.name, elapsed, holdout_metrics.pr_auc, holdout_metrics.roc_auc, holdout_metrics.f1,
        )

        return ModelTrainingResult(
            model_name=self.model_spec.name,
            tuning_result=tuning_result,
            fitted_estimator=estimator,
            threshold_decision=threshold_decision,
            holdout_metrics=holdout_metrics,
            holdout_confusion_matrix=holdout_confusion,
            holdout_roc_curve=holdout_roc,
            holdout_pr_curve=holdout_pr,
            holdout_calibration_curve=holdout_calibration,
            operational_metrics=operational_metrics,
            feature_importance=feature_importance,
            train_seconds=elapsed,
            scale_pos_weight=scale_pos_weight,
        )


def compute_learning_curve(
    model_spec: ModelSpec,
    best_params: dict,
    X_train_core: np.ndarray,
    y_train_core: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    train_size_fractions: tuple[float, ...],
    random_state: int = 42,
) -> pd.DataFrame:
    """Train-set-size vs. validation PR-AUC, for the best model only.

    Uses time-ordered prefixes of ``train_core`` (more historical data as
    the fraction grows), evaluated on the same untouched validation slice
    used for threshold calibration -- not the final test set, since this is
    a diagnostic curve, not part of the leaderboard comparison.
    """
    rows = []
    for fraction in train_size_fractions:
        n = max(int(len(X_train_core) * fraction), 50)
        X_subset, y_subset = X_train_core[:n], y_train_core[:n]
        scale_pos_weight = compute_scale_pos_weight(y_subset)
        estimator = model_spec.build_estimator(best_params, scale_pos_weight, random_state)
        estimator.fit(X_subset, y_subset)
        train_proba = estimator.predict_proba(X_subset)[:, 1]
        val_proba = estimator.predict_proba(X_val)[:, 1]
        from sklearn.metrics import average_precision_score
        rows.append({
            "train_size_fraction": fraction,
            "train_rows": n,
            "train_pr_auc": average_precision_score(y_subset, train_proba),
            "validation_pr_auc": average_precision_score(y_val, val_proba),
        })
    return pd.DataFrame(rows)


def compute_validation_curve(
    model_spec: ModelSpec,
    best_params: dict,
    param_name: str,
    param_values: list,
    X_train_core: np.ndarray,
    y_train_core: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    random_state: int = 42,
) -> pd.DataFrame:
    """Validation PR-AUC as one hyperparameter varies, holding the rest at their tuned values."""
    from sklearn.metrics import average_precision_score
    scale_pos_weight = compute_scale_pos_weight(y_train_core)
    rows = []
    for value in param_values:
        params = dict(best_params)
        params[param_name] = value
        estimator = model_spec.build_estimator(params, scale_pos_weight, random_state)
        estimator.fit(X_train_core, y_train_core)
        train_proba = estimator.predict_proba(X_train_core)[:, 1]
        val_proba = estimator.predict_proba(X_val)[:, 1]
        rows.append({
            param_name: value,
            "train_pr_auc": average_precision_score(y_train_core, train_proba),
            "validation_pr_auc": average_precision_score(y_val, val_proba),
        })
    return pd.DataFrame(rows)
