"""MLflow logging for Module 4's Normal-vs-DP comparison.

Reuses Module 3's ``MLflowTracker`` for tracking-URI/experiment setup and
parent-run creation (both fully generic, no DP-specific behavior needed).
Per-variant (Normal/DP) logging is implemented here directly via the
``mlflow`` library -- the same underlying pattern
``MLflowTracker.log_model_result`` uses internally, just for a different
result shape (:class:`~src.privacy.dp_model.TrainingRunResult` +
:class:`~src.privacy.privacy_accountant.PrivacyBudget` instead of
:class:`~src.models.train.ModelTrainingResult`), so no new abstraction is
forced onto Module 3's class just to fit Module 4's data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import mlflow

from src.evaluation.metrics import ClassificationMetrics
from src.privacy.dp_model import TrainingRunResult
from src.privacy.privacy_accountant import PrivacyBudget
from src.utils.logger import get_logger

logger = get_logger(__name__)


def log_dp_variant_run(
    variant_name: str,
    training_result: TrainingRunResult,
    metrics: ClassificationMetrics,
    dataset_version: str,
    architecture_params: dict,
    batch_size: int,
    epochs: int,
    privacy_params: Optional[dict] = None,
    privacy_budget: Optional[PrivacyBudget] = None,
    artifact_dir: Optional[Path] = None,
) -> str:
    """Logs one trained variant (Normal or DP) as a nested MLflow run."""
    with mlflow.start_run(run_name=variant_name, nested=True) as run:
        mlflow.set_tag("dataset_version", dataset_version)
        mlflow.set_tag("variant", variant_name)
        mlflow.set_tag("milestone", "Milestone 2 - Model Development & Risk Analysis (Module 4: Differential Privacy)")

        mlflow.log_params({f"arch_{k}": v for k, v in architecture_params.items()})
        mlflow.log_param("batch_size", batch_size)
        mlflow.log_param("epochs", epochs)

        if privacy_params:
            mlflow.log_params({f"dp_{k}": v for k, v in privacy_params.items()})
        if privacy_budget is not None:
            mlflow.log_metric("epsilon", privacy_budget.epsilon)
            mlflow.log_metric("epsilon_poisson_assumption", privacy_budget.epsilon_poisson_assumption)
            mlflow.log_metric("delta", privacy_budget.delta)

        for metric_name, value in metrics.to_dict().items():
            mlflow.log_metric(metric_name, value)
        mlflow.log_metric("train_seconds", training_result.train_seconds)

        for epoch_metric_name, values in training_result.history.items():
            for epoch_idx, value in enumerate(values):
                mlflow.log_metric(f"epoch_{epoch_metric_name}", value, step=epoch_idx)

        if artifact_dir is not None and artifact_dir.exists():
            mlflow.log_artifacts(str(artifact_dir), artifact_path=f"evaluation_{variant_name}")

        try:
            mlflow.tensorflow.log_model(training_result.model, name="model")
        except Exception as exc:  # model logging must never break the tracked run
            logger.warning("Could not log %s model artifact to MLflow: %s", variant_name, exc)

        logger.info("Logged %s run to MLflow: run_id=%s", variant_name, run.info.run_id)
        return run.info.run_id
