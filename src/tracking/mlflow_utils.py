"""MLflow experiment tracking wrapper for Module 3.

Every candidate model's tuning parameters, CV/holdout metrics, evaluation
plots, and the fitted model itself are logged as one nested MLflow run under
a single parent "model_comparison" run, so the entire cross-model comparison
for a given dataset version is reconstructable from MLflow alone.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import mlflow

from src.models.train import ModelTrainingResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MLflowTracker:
    def __init__(self, tracking_uri: str, experiment_name: str) -> None:
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)
        self.experiment_name = experiment_name

    def start_parent_run(self, run_name: str, dataset_version: str) -> Any:
        run = mlflow.start_run(run_name=run_name)
        mlflow.set_tag("dataset_version", dataset_version)
        mlflow.set_tag("milestone", "Milestone 2 - Model Development & Risk Analysis")
        return run

    def log_model_result(
        self,
        result: ModelTrainingResult,
        dataset_version: str,
        artifact_dir: Optional[Path] = None,
    ) -> str:
        """Logs one candidate model as a nested run; returns the run id."""
        with mlflow.start_run(run_name=result.model_name, nested=True) as run:
            mlflow.set_tag("dataset_version", dataset_version)
            mlflow.set_tag("model_name", result.model_name)

            mlflow.log_params({f"hp_{k}": v for k, v in result.tuning_result.best_params.items()})
            mlflow.log_param("scale_pos_weight", result.scale_pos_weight)
            mlflow.log_param("threshold_strategy", result.threshold_decision.strategy)
            mlflow.log_param("n_optuna_trials", result.tuning_result.n_trials_completed)

            mlflow.log_metric("cv_pr_auc_mean", result.tuning_result.best_cv_score)
            for i, fold_score in enumerate(result.tuning_result.cv_fold_scores):
                mlflow.log_metric(f"cv_fold_{i}_pr_auc", fold_score)
            for metric_name, value in result.holdout_metrics.to_dict().items():
                mlflow.log_metric(f"holdout_{metric_name}", value)
            mlflow.log_metric("decision_threshold", result.threshold_decision.threshold)
            mlflow.log_metric(
                "recall_at_precision_target", result.operational_metrics["recall_at_precision"]["recall"]
            )
            mlflow.log_metric("train_seconds", result.train_seconds)

            if artifact_dir is not None and artifact_dir.exists():
                mlflow.log_artifacts(str(artifact_dir), artifact_path=f"evaluation_{result.model_name}")

            try:
                self._log_model_flavor(result)
            except Exception as exc:  # model logging must never break the tracked run
                logger.warning("Could not log model artifact for '%s' to MLflow: %s", result.model_name, exc)

            return run.info.run_id

    @staticmethod
    def _log_model_flavor(result: ModelTrainingResult) -> None:
        name = result.model_name
        estimator = result.fitted_estimator
        if name == "xgboost":
            mlflow.xgboost.log_model(estimator, name="model")
        elif name == "lightgbm":
            mlflow.lightgbm.log_model(estimator, name="model")
        elif name == "neural_network":
            mlflow.tensorflow.log_model(estimator.model_, name="model")
        else:
            mlflow.sklearn.log_model(estimator, name="model")
