"""Module 4 entrypoint: Differential Privacy Training (TensorFlow Privacy).

Run from the repository root:

    python scripts/run_module4.py

Pipeline order:

    1. Load Module 2's processed train/test matrices + feature manifest.
    2. Load Module 3's ALREADY-TUNED Neural Network hyperparameters (from
       reports_m3/model_comparison_leaderboard.csv) -- the architecture is
       reused, not redefined.
    3. Time-ordered 3-way split of train (train_core / validation slice),
       same philosophy as Module 3.
    4. Train the Normal NN (Adam) and DP NN (DP-Adam) on train_core, from
       identical initial weights -- only the optimizer differs.
    5. Compute the privacy budget (epsilon, delta) for the DP run via
       TensorFlow Privacy's accountant.
    6. Threshold both models independently on the validation slice, evaluate
       both once on the Module 2 test holdout, and build a data-driven
       Normal-vs-DP comparison.
    7. Run a noise-multiplier sweep for the privacy-utility curve.
    8. Persist both models (weights + full metadata), log everything to
       MLflow, and write the DP report.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Must precede any other import that could transitively import tensorflow --
# see src/privacy/tf_privacy_compat.py for the full explanation.
from src.privacy import tf_privacy_compat  # noqa: E402,F401

import ast
import json

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from src.config.config_loader import AppConfig, load_config
from src.evaluation.plots import plot_pr_curve, plot_roc_curve
from src.models.model_registry import compute_scale_pos_weight
from src.privacy.dp_evaluation import evaluate_and_compare
from src.privacy.dp_mlflow import log_dp_variant_run
from src.privacy.dp_model import DPNeuralNetworkTrainer
from src.privacy.dp_persistence import DPModelArtifact
from src.privacy.dp_plots import plot_privacy_utility_curve, plot_training_curves
from src.privacy.dp_report_builder import DPReportBuilder
from src.privacy.privacy_accountant import PrivacyAccountant
from src.tracking.mlflow_utils import MLflowTracker
from src.utils.logger import configure_logging, get_logger


def _load_processed_split(path: Path, feature_manifest: dict) -> tuple[np.ndarray, np.ndarray]:
    df = pd.read_csv(path)
    metadata_columns = feature_manifest["metadata_columns"]
    target_column = feature_manifest["target_column"]
    feature_columns = [c for c in df.columns if c not in metadata_columns and c != target_column]
    X = df[feature_columns].to_numpy().astype("float32")
    y = df[target_column].to_numpy().astype("float32")
    return X, y


def _load_module3_nn_hyperparameters(leaderboard_path: Path) -> dict:
    """Reads Module 3's already-tuned Neural Network hyperparameters from its
    leaderboard CSV. Deliberately avoids joblib-loading Module 3's saved
    Keras model directly: that model was serialized under standard Keras 3,
    and this process runs under TF_USE_LEGACY_KERAS=1 for TF-Privacy
    compatibility -- loading a Keras-3-serialized model in a legacy-Keras
    process is an unverified cross-version risk. Reading plain hyperparameter
    values from a CSV avoids that risk entirely.
    """
    if not leaderboard_path.exists():
        raise FileNotFoundError(
            f"Module 3 leaderboard not found at {leaderboard_path} -- Module 3 must be run before Module 4."
        )
    df = pd.read_csv(leaderboard_path)
    row = df[df["model_name"] == "neural_network"]
    if row.empty:
        raise ValueError(f"No 'neural_network' row found in {leaderboard_path}.")
    return ast.literal_eval(row.iloc[0]["best_params"])


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
    logger.info("=== Module 4: Differential Privacy Training ===")

    with open(config.paths.feature_manifest_json, "r", encoding="utf-8") as fh:
        feature_manifest = json.load(fh)
    dataset_version = feature_manifest["dataset_version"]

    X_train, y_train = _load_processed_split(config.paths.processed_train_csv, feature_manifest)
    X_test, y_test = _load_processed_split(config.paths.processed_test_csv, feature_manifest)
    logger.info("Loaded processed data: train=%s test=%s", X_train.shape, X_test.shape)

    architecture_params = _load_module3_nn_hyperparameters(
        config.paths_m3.reports_m3_dir / "model_comparison_leaderboard.csv"
    )
    logger.info("Reusing Module 3's tuned NN architecture: %s", architecture_params)

    dp_cfg = config.differential_privacy
    batch_size, epochs = dp_cfg.batch_size, dp_cfg.epochs

    # Same time-ordered train_core / validation-slice split philosophy as
    # Module 3 -- the validation slice is chronologically later and never
    # touched by training, only by threshold calibration.
    validation_fraction = config.threshold_optimization.validation_fraction_of_train
    split_idx = int(len(X_train) * (1 - validation_fraction))
    train_core_X, train_core_y = X_train[:split_idx], y_train[:split_idx]
    val_X, val_y = X_train[split_idx:], y_train[split_idx:]
    logger.info("train_core=%s, validation slice=%s", train_core_X.shape, val_X.shape)

    scale_pos_weight = compute_scale_pos_weight(train_core_y)
    trainer = DPNeuralNetworkTrainer(
        architecture_params=architecture_params,
        class_weight_positive=scale_pos_weight,
        random_state=config.project.random_seed,
    )

    logger.info("--- Training Normal NN ---")
    normal_result = trainer.train_normal(train_core_X, train_core_y, batch_size=batch_size, epochs=epochs)

    logger.info("--- Training DP NN ---")
    dp_result = trainer.train_dp(
        train_core_X, train_core_y, batch_size=batch_size, epochs=epochs,
        l2_norm_clip=dp_cfg.l2_norm_clip, noise_multiplier=dp_cfg.noise_multiplier, microbatches=dp_cfg.microbatches,
    )

    accountant = PrivacyAccountant()
    privacy_budget = accountant.compute(
        num_examples=len(train_core_X), batch_size=batch_size,
        noise_multiplier=dp_cfg.noise_multiplier, epochs=epochs, delta=dp_cfg.delta,
    )

    normal_proba_val = normal_result.model.predict(val_X, verbose=0).ravel()
    dp_proba_val = dp_result.model.predict(val_X, verbose=0).ravel()
    normal_proba_test = normal_result.model.predict(X_test, verbose=0).ravel()
    dp_proba_test = dp_result.model.predict(X_test, verbose=0).ravel()

    comparison = evaluate_and_compare(
        y_val=val_y, normal_proba_val=normal_proba_val, dp_proba_val=dp_proba_val,
        y_test=y_test, normal_proba_test=normal_proba_test, dp_proba_test=dp_proba_test,
        privacy_budget=privacy_budget, l2_norm_clip=dp_cfg.l2_norm_clip,
        threshold_strategy=config.threshold_optimization.strategy,
        threshold_min_precision=config.threshold_optimization.min_precision,
    )

    reports_dir = config.paths_m4.reports_m4_dir
    artifacts_dir = config.paths_m4.artifacts_m4_dir
    reports_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    fpr_n, tpr_n, _ = comparison.normal_roc_curve
    plot_roc_curve(fpr_n, tpr_n, comparison.normal_metrics.roc_auc, "normal_nn", reports_dir / "normal_roc_curve.png")
    fpr_d, tpr_d, _ = comparison.dp_roc_curve
    plot_roc_curve(fpr_d, tpr_d, comparison.dp_metrics.roc_auc, "dp_nn", reports_dir / "dp_roc_curve.png")
    prec_n, rec_n, _ = comparison.normal_pr_curve
    plot_pr_curve(prec_n, rec_n, comparison.normal_metrics.pr_auc, "normal_nn", reports_dir / "normal_pr_curve.png")
    prec_d, rec_d, _ = comparison.dp_pr_curve
    plot_pr_curve(prec_d, rec_d, comparison.dp_metrics.pr_auc, "dp_nn", reports_dir / "dp_pr_curve.png")
    plot_training_curves(normal_result.history, dp_result.history, "loss", reports_dir / "training_curve_loss.png")
    plot_training_curves(normal_result.history, dp_result.history, "pr_auc", reports_dir / "training_curve_pr_auc.png")

    # --- Privacy-utility sweep ---
    logger.info("--- Privacy-utility noise multiplier sweep ---")
    sweep_rows = []
    for nm in dp_cfg.noise_multiplier_sweep:
        logger.info("Sweep point: noise_multiplier=%.3f", nm)
        sweep_result = trainer.train_dp(
            train_core_X, train_core_y, batch_size=batch_size, epochs=epochs,
            l2_norm_clip=dp_cfg.l2_norm_clip, noise_multiplier=nm, microbatches=dp_cfg.microbatches,
        )
        sweep_budget = accountant.compute(
            num_examples=len(train_core_X), batch_size=batch_size,
            noise_multiplier=nm, epochs=epochs, delta=dp_cfg.delta,
        )
        sweep_proba_val = sweep_result.model.predict(val_X, verbose=0).ravel()
        sweep_rows.append({
            "noise_multiplier": nm,
            "epsilon": sweep_budget.epsilon,
            "pr_auc": average_precision_score(val_y, sweep_proba_val),
            "roc_auc": roc_auc_score(val_y, sweep_proba_val),
        })
    sweep_df = pd.DataFrame(sweep_rows)
    sweep_df.to_csv(reports_dir / "privacy_utility_sweep.csv", index=False)
    plot_privacy_utility_curve(sweep_df, "pr_auc", reports_dir / "privacy_utility_curve.png")

    # --- Persistence ---
    DPModelArtifact.save(
        model=normal_result.model, variant="normal", dataset_version=dataset_version,
        architecture_params=architecture_params, batch_size=batch_size, epochs=epochs,
        train_seconds=normal_result.train_seconds, random_state=config.project.random_seed,
        output_dir=artifacts_dir / "normal_nn",
    )
    dp_privacy_params = {
        "l2_norm_clip": dp_cfg.l2_norm_clip, "noise_multiplier": dp_cfg.noise_multiplier,
        "microbatches": dp_cfg.microbatches,
    }
    DPModelArtifact.save(
        model=dp_result.model, variant="dp", dataset_version=dataset_version,
        architecture_params=architecture_params, batch_size=batch_size, epochs=epochs,
        train_seconds=dp_result.train_seconds, random_state=config.project.random_seed,
        output_dir=artifacts_dir / "dp_nn",
        privacy_params=dp_privacy_params, privacy_budget=privacy_budget,
    )

    # --- MLflow ---
    tracker = MLflowTracker(config.mlflow.tracking_uri, config.mlflow.experiment_name)
    with tracker.start_parent_run(run_name="differential_privacy_comparison", dataset_version=dataset_version):
        log_dp_variant_run(
            "normal_nn", normal_result, comparison.normal_metrics, dataset_version,
            architecture_params, batch_size, epochs, artifact_dir=reports_dir,
        )
        log_dp_variant_run(
            "dp_nn", dp_result, comparison.dp_metrics, dataset_version,
            architecture_params, batch_size, epochs,
            privacy_params=dp_privacy_params, privacy_budget=privacy_budget, artifact_dir=reports_dir,
        )

    # --- Report ---
    DPReportBuilder().build(
        architecture_params=architecture_params, batch_size=batch_size, epochs=epochs,
        l2_norm_clip=dp_cfg.l2_norm_clip, noise_multiplier=dp_cfg.noise_multiplier, microbatches=dp_cfg.microbatches,
        privacy_budget=privacy_budget, normal_result=normal_result, dp_result=dp_result,
        comparison=comparison, sweep_df=sweep_df, dataset_version=dataset_version,
        output_path=reports_dir / "dp_report.md",
    )

    print(f"Normal NN: PR-AUC={comparison.normal_metrics.pr_auc:.4f}, ROC-AUC={comparison.normal_metrics.roc_auc:.4f}")
    print(f"DP NN:     PR-AUC={comparison.dp_metrics.pr_auc:.4f}, ROC-AUC={comparison.dp_metrics.roc_auc:.4f}")
    print(f"Privacy budget: epsilon={privacy_budget.epsilon:.4f}, delta={privacy_budget.delta:.1e}")

    logger.info("Module 4 completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
