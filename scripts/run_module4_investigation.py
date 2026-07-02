"""Module 4 root-cause investigation: why is the DP model's utility so poor?

A controlled, one-factor-at-a-time experimental investigation, NOT a guess.
Phases:

    Phase 0: Gradient-norm diagnostic (already run interactively; informs
             the l2_norm_clip range tested below).
    Phase A: l2_norm_clip sweep, everything else fixed at the original
             Module 4 configuration.
    Phase B: class_weight ablation at the best clip found in Phase A --
             the gradient diagnostic showed class_weight's ~36x amplification
             is a major contributor to the extreme pre-clip gradient tail,
             so this is tested directly, not assumed.
    Phase C: learning_rate sweep at the best (clip, class_weight) found.
    Phase D: confirmation run of the best overall configuration on the FULL
             dataset, compared directly against the Normal NN and the
             original Module 4 DP baseline.

Exploration (Phases A-C) runs on a representative 100,000-row subsample of
train_core (not the full 401K rows) purely for iteration speed -- an
explicit, documented tractability choice consistent with this project's
established precedent (Module 2/3's sampling for expensive search steps).
The WINNING configuration is always re-confirmed on the full dataset before
being reported as a result (Phase D), so no conclusion in the final report
rests only on the small-sample numbers.

All exploratory evaluation happens on the VALIDATION slice, never the test
set -- the test set is touched only once, in Phase D, for the final
confirmed comparison, so config selection here cannot leak into the
reported test metrics.
"""

from __future__ import annotations

import ast
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.privacy import tf_privacy_compat  # noqa: E402,F401

import numpy as np
import pandas as pd

from src.config.config_loader import load_config
from src.models.model_registry import compute_scale_pos_weight
from src.privacy.dp_diagnostics import run_gradient_norm_diagnostic
from src.privacy.dp_experiment import run_dp_experiment
from src.privacy.dp_model import DPNeuralNetworkTrainer
from src.utils.logger import configure_logging, get_logger

EXPLORATION_SAMPLE_SIZE = 100_000


def _load_processed_split(path: Path, feature_manifest: dict) -> tuple[np.ndarray, np.ndarray]:
    df = pd.read_csv(path)
    metadata_columns = feature_manifest["metadata_columns"]
    target_column = feature_manifest["target_column"]
    feature_columns = [c for c in df.columns if c not in metadata_columns and c != target_column]
    X = df[feature_columns].to_numpy().astype("float32")
    y = df[target_column].to_numpy().astype("float32")
    return X, y


def main() -> int:
    config = load_config()
    configure_logging(
        logs_dir=config.paths.logs_dir, file_name=config.logging.file_name,
        level=config.logging.level, max_bytes=config.logging.max_bytes, backup_count=config.logging.backup_count,
    )
    logger = get_logger(__name__)
    logger.info("=== Module 4 Investigation: Root-Cause Analysis of DP Utility Loss ===")

    with open(config.paths.feature_manifest_json, "r", encoding="utf-8") as fh:
        feature_manifest = json.load(fh)

    X_train, y_train = _load_processed_split(config.paths.processed_train_csv, feature_manifest)
    X_test, y_test = _load_processed_split(config.paths.processed_test_csv, feature_manifest)

    architecture_params = ast.literal_eval(
        pd.read_csv(config.paths_m3.reports_m3_dir / "model_comparison_leaderboard.csv")
        .pipe(lambda df: df[df["model_name"] == "neural_network"])
        .iloc[0]["best_params"]
    )
    logger.info("Architecture (from Module 3): %s", architecture_params)

    dp_cfg = config.differential_privacy
    validation_fraction = config.threshold_optimization.validation_fraction_of_train
    split_idx = int(len(X_train) * (1 - validation_fraction))
    train_core_X_full, train_core_y_full = X_train[:split_idx], y_train[:split_idx]
    val_X, val_y = X_train[split_idx:], y_train[split_idx:]

    # --- Exploration subsample (time-ordered prefix, same convention as
    # the rest of this project's sampling for expensive search steps) ---
    n_explore = min(EXPLORATION_SAMPLE_SIZE, len(train_core_X_full))
    explore_X, explore_y = train_core_X_full[:n_explore], train_core_y_full[:n_explore]
    logger.info("Exploration subsample: %d rows (of %d full train_core rows)", n_explore, len(train_core_X_full))

    original_scale_pos_weight = compute_scale_pos_weight(explore_y)
    logger.info("Original class_weight (scale_pos_weight) on exploration subsample: %.3f", original_scale_pos_weight)

    reports_dir = config.paths_m4.reports_m4_dir / "investigation"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Phase 0: Gradient-norm diagnostic
    # ------------------------------------------------------------------
    logger.info("--- Phase 0: Gradient-norm diagnostic ---")
    diag_trainer = DPNeuralNetworkTrainer(
        architecture_params=architecture_params, class_weight_positive=original_scale_pos_weight,
        random_state=config.project.random_seed,
    )
    diag_model = diag_trainer._build_architecture(explore_X.shape[1])  # noqa: SLF001
    gradient_reports = run_gradient_norm_diagnostic(
        diag_model, explore_X, explore_y,
        class_weight={0: 1.0, 1: original_scale_pos_weight}, l2_norm_clip=dp_cfg.l2_norm_clip, n_samples=300,
    )
    gradient_df = pd.DataFrame([r.to_dict() for r in gradient_reports.values()])
    gradient_df.to_csv(reports_dir / "phase0_gradient_norm_diagnostic.csv", index=False)

    all_results: list = []

    # ------------------------------------------------------------------
    # Phase A: l2_norm_clip sweep
    # ------------------------------------------------------------------
    logger.info("--- Phase A: l2_norm_clip sweep (class_weight and learning_rate fixed at original values) ---")
    clip_values = [0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0]
    trainer_a = DPNeuralNetworkTrainer(
        architecture_params=architecture_params, class_weight_positive=original_scale_pos_weight,
        random_state=config.project.random_seed,
    )
    for clip in clip_values:
        result = run_dp_experiment(
            experiment_name=f"phaseA_clip_{clip}", trainer=trainer_a,
            X_train_core=explore_X, y_train_core=explore_y, X_val=val_X, y_val=val_y,
            batch_size=dp_cfg.batch_size, epochs=dp_cfg.epochs,
            l2_norm_clip=clip, noise_multiplier=dp_cfg.noise_multiplier, microbatches=dp_cfg.microbatches,
            delta=dp_cfg.delta, threshold_strategy=config.threshold_optimization.strategy,
            threshold_min_precision=config.threshold_optimization.min_precision,
        )
        all_results.append(result)

    phase_a_df = pd.DataFrame([r.to_row() for r in all_results])
    phase_a_df.to_csv(reports_dir / "phaseA_l2_norm_clip_sweep.csv", index=False)
    best_clip_row = max(all_results, key=lambda r: r.roc_auc)
    best_clip = best_clip_row.l2_norm_clip
    logger.info("Phase A best l2_norm_clip=%.2f (ROC-AUC=%.4f)", best_clip, best_clip_row.roc_auc)

    # ------------------------------------------------------------------
    # Phase B: class_weight ablation at best clip
    # ------------------------------------------------------------------
    logger.info("--- Phase B: class_weight ablation at l2_norm_clip=%.2f ---", best_clip)
    class_weight_values = [1.0, float(np.sqrt(original_scale_pos_weight)), original_scale_pos_weight]
    phase_b_results = []
    for cw in class_weight_values:
        trainer_b = DPNeuralNetworkTrainer(
            architecture_params=architecture_params, class_weight_positive=cw,
            random_state=config.project.random_seed,
        )
        result = run_dp_experiment(
            experiment_name=f"phaseB_cw_{cw:.2f}", trainer=trainer_b,
            X_train_core=explore_X, y_train_core=explore_y, X_val=val_X, y_val=val_y,
            batch_size=dp_cfg.batch_size, epochs=dp_cfg.epochs,
            l2_norm_clip=best_clip, noise_multiplier=dp_cfg.noise_multiplier, microbatches=dp_cfg.microbatches,
            delta=dp_cfg.delta, threshold_strategy=config.threshold_optimization.strategy,
            threshold_min_precision=config.threshold_optimization.min_precision,
        )
        phase_b_results.append(result)
    all_results.extend(phase_b_results)

    phase_b_df = pd.DataFrame([r.to_row() for r in phase_b_results])
    phase_b_df.to_csv(reports_dir / "phaseB_class_weight_ablation.csv", index=False)
    best_cw_row = max(phase_b_results, key=lambda r: r.roc_auc)
    best_cw = best_cw_row.class_weight_positive
    logger.info("Phase B best class_weight=%.3f (ROC-AUC=%.4f)", best_cw, best_cw_row.roc_auc)

    # ------------------------------------------------------------------
    # Phase C: learning_rate sweep at best (clip, class_weight)
    # ------------------------------------------------------------------
    logger.info("--- Phase C: learning_rate sweep at l2_norm_clip=%.2f, class_weight=%.3f ---", best_clip, best_cw)
    lr_values = [1e-4, 5e-4, architecture_params["learning_rate"], 5e-3, 1e-2]
    phase_c_results = []
    for lr in lr_values:
        arch_c = dict(architecture_params, learning_rate=lr)
        trainer_c = DPNeuralNetworkTrainer(
            architecture_params=arch_c, class_weight_positive=best_cw, random_state=config.project.random_seed,
        )
        result = run_dp_experiment(
            experiment_name=f"phaseC_lr_{lr:.5f}", trainer=trainer_c,
            X_train_core=explore_X, y_train_core=explore_y, X_val=val_X, y_val=val_y,
            batch_size=dp_cfg.batch_size, epochs=dp_cfg.epochs,
            l2_norm_clip=best_clip, noise_multiplier=dp_cfg.noise_multiplier, microbatches=dp_cfg.microbatches,
            delta=dp_cfg.delta, threshold_strategy=config.threshold_optimization.strategy,
            threshold_min_precision=config.threshold_optimization.min_precision,
        )
        phase_c_results.append(result)
    all_results.extend(phase_c_results)

    phase_c_df = pd.DataFrame([r.to_row() for r in phase_c_results])
    phase_c_df.to_csv(reports_dir / "phaseC_learning_rate_sweep.csv", index=False)
    best_lr_row = max(phase_c_results, key=lambda r: r.roc_auc)
    best_lr = best_lr_row.learning_rate
    logger.info("Phase C best learning_rate=%.5f (ROC-AUC=%.4f)", best_lr, best_lr_row.roc_auc)

    # ------------------------------------------------------------------
    # Save full combined results table
    # ------------------------------------------------------------------
    combined_df = pd.DataFrame([r.to_row() for r in all_results])
    combined_df.to_csv(reports_dir / "all_experiments_combined.csv", index=False)

    summary = {
        "best_l2_norm_clip": best_clip,
        "best_class_weight_positive": best_cw,
        "best_learning_rate": best_lr,
        "best_roc_auc_on_exploration_val": best_lr_row.roc_auc,
        "exploration_sample_size": n_explore,
        "original_config": {
            "l2_norm_clip": dp_cfg.l2_norm_clip,
            "class_weight_positive": original_scale_pos_weight,
            "learning_rate": architecture_params["learning_rate"],
        },
    }
    with open(reports_dir / "investigation_summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    print(json.dumps(summary, indent=2))
    logger.info("Investigation phases A-C complete. Run scripts/run_module4_confirmation.py next for Phase D.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
