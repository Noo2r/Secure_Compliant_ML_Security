"""Azure ML Model Registry integration -- ready-to-run, config-driven.

Consistent with Modules 1-2: this code is fully correct and ready to execute
against a real Azure ML workspace, but is never invoked unless
``config.azure_ml.is_configured`` is true (i.e. ``AZURE_SUBSCRIPTION_ID``,
``AZURE_RESOURCE_GROUP``, and ``AZURE_ML_WORKSPACE`` are all set in the
environment). The ``azure-ai-ml`` package import itself is deferred into the
function body so this module remains importable even when that optional
dependency isn't installed in a local/dev environment.
"""

from __future__ import annotations

from pathlib import Path

from src.config.config_loader import AppConfig
from src.evaluation.comparison import BestModelSelection
from src.models.train import ModelTrainingResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


def register_best_model(
    config: AppConfig,
    selection: BestModelSelection,
    result: ModelTrainingResult,
    inference_bundle_path: Path,
    dataset_version: str,
) -> str | None:
    """Registers the winning model + its complete inference bundle in Azure ML.

    Returns the registered model's Azure ML identifier, or ``None`` if Azure
    ML credentials are not configured -- in which case this is a documented,
    logged no-op rather than a silent skip or a crash.
    """
    if not config.azure_ml.is_configured:
        logger.info(
            "Azure ML credentials not configured (AZURE_SUBSCRIPTION_ID/AZURE_RESOURCE_GROUP/"
            "AZURE_ML_WORKSPACE unset) -- skipping live registration. The registration code path "
            "below is ready to run once credentials are supplied."
        )
        return None

    from azure.ai.ml import MLClient
    from azure.ai.ml.entities import Model
    from azure.ai.ml.constants import AssetTypes
    from azure.identity import DefaultAzureCredential

    ml_client = MLClient(
        credential=DefaultAzureCredential(),
        subscription_id=config.azure_ml.subscription_id,
        resource_group_name=config.azure_ml.resource_group,
        workspace_name=config.azure_ml.workspace_name,
    )

    model_asset = Model(
        path=str(inference_bundle_path),
        type=AssetTypes.CUSTOM_MODEL,
        name=config.azure_ml.model_registry_name,
        description=(
            f"Fraud detection model ({result.model_name}), selected by: {selection.justification}"
        ),
        tags={
            "dataset_version": dataset_version,
            "model_name": result.model_name,
            "holdout_pr_auc": f"{result.holdout_metrics.pr_auc:.4f}",
            "holdout_roc_auc": f"{result.holdout_metrics.roc_auc:.4f}",
            "decision_threshold": f"{result.threshold_decision.threshold:.4f}",
            "milestone": "Milestone 2 - Model Development & Risk Analysis",
        },
    )
    registered = ml_client.models.create_or_update(model_asset)
    logger.info("Registered model '%s' version '%s' in Azure ML", registered.name, registered.version)
    return f"{registered.name}:{registered.version}"
