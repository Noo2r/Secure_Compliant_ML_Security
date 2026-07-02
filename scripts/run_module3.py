"""Module 3 entrypoint: Model Development, Hyperparameter Optimization & Evaluation.

Run from the repository root:

    python scripts/run_module3.py

Pipeline order:

    1. Load Module 2's processed train/test matrices + feature manifest.
    2. Load Module 2's fitted engineering/selection/preprocessing pipelines
       (reused as-is for every candidate model's inference bundle -- never
       refit here).
    3. For each candidate model: tune (Optuna + time-aware CV) -> refit on
       train_core -> calibrate a decision threshold on a held-out validation
       slice -> evaluate once on the Module 2 test holdout -> persist a
       complete, self-contained InferenceBundle -> log to MLflow.
    4. Build the cross-model leaderboard, select the best model, run a
       paired statistical comparison between the top two.
    5. Learning/validation curves for the best model only.
    6. Register the best model to Azure ML (ready-to-run, skipped without
       credentials).
    7. Write the Model Development Report, Model Card, and Hyperparameter
       Tuning Report.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import joblib
import numpy as np
import pandas as pd

from src.config.config_loader import AppConfig, load_config
from src.evaluation.comparison import build_leaderboard, compare_top_models_statistically, select_best_model
from src.evaluation.plots import (
    plot_calibration_curve,
    plot_confusion_matrix,
    plot_feature_importance,
    plot_learning_curve,
    plot_lift_gain,
    plot_pr_curve,
    plot_roc_curve,
    plot_validation_curve,
)
from src.evaluation.report_builder import ModelDevelopmentReportBuilder
from src.models.inference_bundle import InferenceBundle
from src.models.model_registry import get_model_spec
from src.models.train import ModelTrainer, compute_learning_curve, compute_validation_curve
from src.registry.azure_ml_registry import register_best_model
from src.tracking.mlflow_utils import MLflowTracker
from src.utils.logger import configure_logging, get_logger

# One representative hyperparameter per model family, varied for the
# best-model-only validation curve (see approved Module 3 plan).
_VALIDATION_CURVE_PARAM_BY_MODEL = {
    "logistic_regression": "C",
    "random_forest": "max_depth",
    "xgboost": "max_depth",
    "lightgbm": "num_leaves",
    "neural_network": "units",
}


def _load_processed_split(path: Path, feature_manifest: dict) -> tuple[np.ndarray, np.ndarray, list[str]]:
    df = pd.read_csv(path)
    metadata_columns = feature_manifest["metadata_columns"]
    target_column = feature_manifest["target_column"]
    feature_columns = [c for c in df.columns if c not in metadata_columns and c != target_column]
    X = df[feature_columns].to_numpy()
    y = df[target_column].to_numpy()
    return X, y, feature_columns


def _validation_curve_param_range(param_name: str, best_value, n_points: int) -> list:
    if param_name == "units":
        return [16, 32, 64, 128]
    if param_name == "C":
        low = max(float(best_value) / 10, 1e-3)
        high = float(best_value) * 10
        return [round(v, 5) for v in np.geomspace(low, high, n_points)]
    if isinstance(best_value, (int, np.integer)):
        low = max(2, int(best_value) - n_points // 2 * 2)
        return list(range(low, low + n_points * 2, 2))
    return [best_value]


def main() -> int:
    config: AppConfig = load_config()
    configure_logging(
        logs_dir=config.paths.logs_dir,
        file_name=config.logging.file_name,
        level=config.logging.level,
        max_bytes=config.logging.max_bytes,
        backup_count=config.logging.backup_count,
    )
    logger = get_logger(__name__)
    logger.info("=== Module 3: Model Development & Hyperparameter Optimization ===")

    with open(config.paths.feature_manifest_json, "r", encoding="utf-8") as fh:
        feature_manifest = json.load(fh)
    dataset_version = feature_manifest["dataset_version"]

    X_train, y_train, feature_names = _load_processed_split(config.paths.processed_train_csv, feature_manifest)
    X_test, y_test, _ = _load_processed_split(config.paths.processed_test_csv, feature_manifest)
    logger.info(
        "Loaded processed data: train=%s test=%s, %d model features",
        X_train.shape, X_test.shape, len(feature_names),
    )

    # Module 2's fitted stages -- loaded once, reused (never refit) for every
    # candidate model's InferenceBundle.
    artifact_paths = feature_manifest["artifact_paths"]
    engineering_pipeline = joblib.load(Path(artifact_paths["engineering_pipeline"]))
    column_selector = joblib.load(Path(artifact_paths["column_selector"]))
    preprocessing_pipeline = joblib.load(Path(artifact_paths["preprocessing_pipeline"]))

    artifacts_dir = config.paths_m3.artifacts_m3_dir
    reports_dir = config.paths_m3.reports_m3_dir
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    tracker = MLflowTracker(config.mlflow.tracking_uri, config.mlflow.experiment_name)
    results = []

    with tracker.start_parent_run(run_name="model_comparison", dataset_version=dataset_version):
        for model_name in config.model_development.candidate_models:
            logger.info("--- Training candidate model: %s ---", model_name)
            model_spec = get_model_spec(model_name)
            trainer = ModelTrainer(
                model_spec=model_spec,
                cv_folds=config.model_development.cv_folds,
                n_trials=config.model_development.optuna_trials[model_name],
                timeout_seconds=config.model_development.optuna_timeout_seconds,
                tuning_sample_size=config.model_development.tuning_sample_size,
                threshold_strategy=config.threshold_optimization.strategy,
                threshold_min_precision=config.threshold_optimization.min_precision,
                validation_fraction_of_train=config.threshold_optimization.validation_fraction_of_train,
                precision_threshold=config.operational_metrics.precision_threshold,
                top_k_values=config.operational_metrics.top_k_values,
                random_state=config.project.random_seed,
            )
            result = trainer.train_and_evaluate(X_train, y_train, X_test, y_test, feature_names)
            results.append(result)

            model_report_dir = reports_dir / model_name
            fpr, tpr, _ = result.holdout_roc_curve
            plot_roc_curve(fpr, tpr, result.holdout_metrics.roc_auc, model_name, model_report_dir / "roc_curve.png")
            precision, recall, _ = result.holdout_pr_curve
            plot_pr_curve(precision, recall, result.holdout_metrics.pr_auc, model_name, model_report_dir / "pr_curve.png")
            plot_confusion_matrix(result.holdout_confusion_matrix, model_name, model_report_dir / "confusion_matrix.png")
            prob_true, prob_pred = result.holdout_calibration_curve
            plot_calibration_curve(prob_true, prob_pred, model_name, model_report_dir / "calibration_curve.png")
            plot_lift_gain(result.operational_metrics["lift_and_gain"], model_name, model_report_dir / "lift_gain.png")
            result.operational_metrics["lift_and_gain"].to_csv(model_report_dir / "lift_and_gain.csv", index=False)
            if result.feature_importance is not None:
                plot_feature_importance(result.feature_importance, model_name, model_report_dir / "feature_importance.png")
                result.feature_importance.to_csv(model_report_dir / "feature_importance.csv")

            bundle = InferenceBundle(
                model_name=model_name,
                engineering_pipeline=engineering_pipeline,
                column_selector=column_selector,
                preprocessing_pipeline=preprocessing_pipeline,
                estimator=result.fitted_estimator,
                threshold_decision=result.threshold_decision,
                dataset_version=dataset_version,
            )
            bundle.save(artifacts_dir / f"{model_name}_inference_bundle.joblib")

            tracker.log_model_result(result, dataset_version, artifact_dir=model_report_dir)

        leaderboard = build_leaderboard(results)
        leaderboard.to_csv(reports_dir / "model_comparison_leaderboard.csv", index=False)
        selection = select_best_model(leaderboard, config.model_development.tie_break_relative_tolerance)

        top_two = leaderboard["model_name"].head(2).tolist()
        statistical_comparison = (
            compare_top_models_statistically(results, top_two[0], top_two[1]) if len(top_two) == 2 else {}
        )
        with open(reports_dir / "top_model_statistical_comparison.json", "w", encoding="utf-8") as fh:
            json.dump(statistical_comparison, fh, indent=2)

        best_result = next(r for r in results if r.model_name == selection.model_name)
        best_spec = get_model_spec(selection.model_name)

        validation_fraction = config.threshold_optimization.validation_fraction_of_train
        split_idx = int(len(X_train) * (1 - validation_fraction))
        train_core_X, train_core_y = X_train[:split_idx], y_train[:split_idx]
        val_X, val_y = X_train[split_idx:], y_train[split_idx:]

        learning_curve_df = compute_learning_curve(
            best_spec, best_result.tuning_result.best_params, train_core_X, train_core_y, val_X, val_y,
            config.model_development.learning_curve_train_sizes, config.project.random_seed,
        )
        learning_curve_df.to_csv(reports_dir / "best_model_learning_curve.csv", index=False)
        plot_learning_curve(learning_curve_df, selection.model_name, reports_dir / "best_model_learning_curve.png")

        val_param_name = _VALIDATION_CURVE_PARAM_BY_MODEL[selection.model_name]
        best_value = best_result.tuning_result.best_params.get(val_param_name)
        param_values = _validation_curve_param_range(val_param_name, best_value, config.model_development.validation_curve_points)
        validation_curve_df = compute_validation_curve(
            best_spec, best_result.tuning_result.best_params, val_param_name, param_values,
            train_core_X, train_core_y, val_X, val_y, config.project.random_seed,
        )
        validation_curve_df.to_csv(reports_dir / "best_model_validation_curve.csv", index=False)
        plot_validation_curve(
            validation_curve_df, val_param_name, selection.model_name, reports_dir / "best_model_validation_curve.png"
        )

        best_bundle_path = artifacts_dir / f"{selection.model_name}_inference_bundle.joblib"
        azure_model_id = register_best_model(config, selection, best_result, best_bundle_path, dataset_version)

    ModelDevelopmentReportBuilder().build(
        results=results,
        leaderboard=leaderboard,
        selection=selection,
        statistical_comparison=statistical_comparison,
        dataset_version=dataset_version,
        azure_model_id=azure_model_id,
        output_dir=reports_dir,
    )

    print(leaderboard.to_string(index=False))
    print(f"\nBest model: {selection.model_name}\n{selection.justification}")
    print(f"Azure ML: {azure_model_id or 'registration skipped (no credentials configured)'}")

    logger.info("Module 3 completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
