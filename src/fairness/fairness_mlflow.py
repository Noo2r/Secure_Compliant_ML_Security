"""MLflow logging for Module 5, mirroring Module 4's ``dp_mlflow.py`` pattern:
one parent run for the whole fairness analysis, with all metrics, CSVs,
JSON summaries, and plots logged as parameters/metrics/artifacts.
"""

from __future__ import annotations

from pathlib import Path

import mlflow

from src.fairness.fairness_report_builder import AttributeFairnessResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FairnessMLflowLogger:
    def __init__(self, tracking_uri: str, experiment_name: str) -> None:
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)

    def log_fairness_run(
        self, model_name: str, dataset_version: str, results: list[AttributeFairnessResult], artifact_dir: Path
    ) -> str:
        with mlflow.start_run(run_name="fairness_analysis") as run:
            mlflow.set_tag("dataset_version", dataset_version)
            mlflow.set_tag("model_name", model_name)
            mlflow.set_tag("milestone", "Milestone 2 - Model Development & Risk Analysis")
            mlflow.log_param("model_analyzed", model_name)
            mlflow.log_param("n_attributes_analyzed", len(results))

            for result in results:
                prefix = f"{result.attribute_name}"
                for group, gm in result.group_metrics.items():
                    safe_group = str(group).replace(" ", "_")
                    mlflow.log_metric(f"{prefix}.{safe_group}.selection_rate", gm.selection_rate)
                    mlflow.log_metric(f"{prefix}.{safe_group}.tpr", gm.tpr)
                    mlflow.log_metric(f"{prefix}.{safe_group}.fpr", gm.fpr)
                    mlflow.log_metric(f"{prefix}.{safe_group}.fnr", gm.fnr)
                    mlflow.log_metric(f"{prefix}.{safe_group}.f1", gm.f1)
                    mlflow.log_metric(f"{prefix}.{safe_group}.balanced_accuracy", gm.balanced_accuracy)
                for group, pm in result.pairwise_metrics.items():
                    safe_group = str(group).replace(" ", "_")
                    mlflow.log_metric(f"{prefix}.{safe_group}.spd", pm.statistical_parity_difference)
                    mlflow.log_metric(f"{prefix}.{safe_group}.dir", pm.disparate_impact_ratio)
                    mlflow.log_metric(f"{prefix}.{safe_group}.eod", pm.equal_opportunity_difference)
                    mlflow.log_metric(f"{prefix}.{safe_group}.aod", pm.average_odds_difference)
                if result.significance_result:
                    mlflow.log_metric(f"{prefix}.significance_p_value", result.significance_result.p_value)

            if artifact_dir.exists():
                mlflow.log_artifacts(str(artifact_dir), artifact_path="fairness_analysis")

            logger.info("Logged fairness analysis run to MLflow: run_id=%s", run.info.run_id)
            return run.info.run_id
