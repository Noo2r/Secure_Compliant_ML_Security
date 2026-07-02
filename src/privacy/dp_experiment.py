"""Controlled single-experiment runner for the Module 4 root-cause
investigation.

One function, one experiment: trains a DP model at a given hyperparameter
configuration, evaluates it fully (all metrics the investigation requires),
and returns a flat, DataFrame-appendable record. Used by
``scripts/run_module4_investigation.py`` to run every sweep with identical
methodology, so results across experiments are directly comparable -- the
whole point of "change one factor at a time".
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Optional

import numpy as np

from src.evaluation.metrics import compute_classification_metrics, compute_confusion_matrix
from src.models.threshold import optimize_threshold
from src.privacy.dp_model import DPNeuralNetworkTrainer
from src.privacy.privacy_accountant import PrivacyAccountant
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class DPExperimentResult:
    experiment_name: str
    l2_norm_clip: float
    noise_multiplier: float
    learning_rate: float
    class_weight_positive: float
    batch_size: int
    epochs: int
    epsilon: float
    delta: float
    train_seconds: float
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    pr_auc: float
    threshold: float
    confusion_matrix: dict
    loss_history: list
    pred_mean: float
    pred_median: float
    pred_std: float
    pred_p90: float
    pred_p99: float
    pred_max: float
    pred_n_unique_rounded4: int

    def to_row(self) -> dict:
        d = asdict(self)
        d["confusion_matrix"] = str(d["confusion_matrix"])
        d["loss_history"] = str(d["loss_history"])
        return d


def run_dp_experiment(
    experiment_name: str,
    trainer: DPNeuralNetworkTrainer,
    X_train_core: np.ndarray,
    y_train_core: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    batch_size: int,
    epochs: int,
    l2_norm_clip: float,
    noise_multiplier: float,
    microbatches: int,
    delta: float,
    threshold_strategy: str = "max_f1",
    threshold_min_precision: float = 0.5,
) -> DPExperimentResult:
    """Trains and fully evaluates one DP configuration on the validation
    slice (not the final test set -- exploratory sweeps must not touch the
    test set, or later "confirm on test" numbers would be contaminated by
    having implicitly selected the winning config using test performance).
    """
    result = trainer.train_dp(
        X_train_core, y_train_core, batch_size=batch_size, epochs=epochs,
        l2_norm_clip=l2_norm_clip, noise_multiplier=noise_multiplier, microbatches=microbatches,
    )
    accountant = PrivacyAccountant()
    budget = accountant.compute(
        num_examples=len(X_train_core), batch_size=batch_size,
        noise_multiplier=noise_multiplier, epochs=epochs, delta=delta,
    )

    proba_val = result.model.predict(X_val, verbose=0).ravel()
    threshold_decision = optimize_threshold(y_val, proba_val, threshold_strategy, threshold_min_precision)
    metrics = compute_classification_metrics(y_val, proba_val, threshold_decision.threshold)
    cm = compute_confusion_matrix(y_val, proba_val, threshold_decision.threshold)

    exp_result = DPExperimentResult(
        experiment_name=experiment_name,
        l2_norm_clip=l2_norm_clip,
        noise_multiplier=noise_multiplier,
        learning_rate=trainer.architecture_params["learning_rate"],
        class_weight_positive=trainer.class_weight_positive,
        batch_size=batch_size,
        epochs=epochs,
        epsilon=budget.epsilon,
        delta=budget.delta,
        train_seconds=result.train_seconds,
        accuracy=metrics.accuracy,
        precision=metrics.precision,
        recall=metrics.recall,
        f1=metrics.f1,
        roc_auc=metrics.roc_auc,
        pr_auc=metrics.pr_auc,
        threshold=threshold_decision.threshold,
        confusion_matrix=cm,
        loss_history=result.history.get("loss", []),
        pred_mean=float(np.mean(proba_val)),
        pred_median=float(np.median(proba_val)),
        pred_std=float(np.std(proba_val)),
        pred_p90=float(np.percentile(proba_val, 90)),
        pred_p99=float(np.percentile(proba_val, 99)),
        pred_max=float(np.max(proba_val)),
        pred_n_unique_rounded4=int(len(np.unique(np.round(proba_val, 4)))),
    )
    logger.info(
        "[%s] l2_norm_clip=%.2f noise_mult=%.2f cw_pos=%.2f -> ROC-AUC=%.4f PR-AUC=%.4f "
        "epsilon=%.2f pred_mean=%.5f train_s=%.1f",
        experiment_name, l2_norm_clip, noise_multiplier, trainer.class_weight_positive,
        exp_result.roc_auc, exp_result.pr_auc, exp_result.epsilon, exp_result.pred_mean, exp_result.train_seconds,
    )
    return exp_result
