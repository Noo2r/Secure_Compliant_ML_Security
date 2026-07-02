"""Module 5 entrypoint: Fairness Analysis.

Run from the repository root:

    python scripts/run_module5.py

Primary model analyzed: Module 3's LightGBM (the production model,
`artifacts_m3/lightgbm_inference_bundle.joblib`). The Module 4 DP model is
analyzed only as an OPTIONAL secondary comparison on the primary protected
attribute, per the project brief -- never as the primary fairness subject.

Data: Module 2's `data/processed/test.csv`, which already contains the
protected/proxy attributes (`card6`, `card4`, `DeviceType`) as preserved,
non-feature metadata columns -- no new data loading or feature engineering.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.privacy import tf_privacy_compat  # noqa: E402,F401 -- must precede tensorflow import if DP comparison runs

import joblib
import numpy as np
import pandas as pd

from src.config.config_loader import AppConfig, load_config
from src.fairness.attribute_analysis import analyze_protected_attribute
from src.fairness.fairlearn_validation import is_fairlearn_available
from src.fairness.fairness_mlflow import FairnessMLflowLogger
from src.fairness.fairness_plots import (
    plot_disparate_impact,
    plot_error_rate_comparison,
    plot_fairness_dashboard,
    plot_fairness_metric_bars,
    plot_group_confusion_matrices,
    plot_pr_per_group,
    plot_roc_per_group,
    plot_selection_rate_comparison,
)
from src.fairness.fairness_report_builder import FairnessReportBuilder
from src.utils.logger import configure_logging, get_logger


def _load_test_set(config: AppConfig, feature_manifest: dict) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, list[str]]:
    df = pd.read_csv(config.paths.processed_test_csv)
    metadata_columns = feature_manifest["metadata_columns"]
    target_column = feature_manifest["target_column"]
    feature_columns = [c for c in df.columns if c not in metadata_columns and c != target_column]
    X = df[feature_columns].to_numpy()
    y = df[target_column].to_numpy()
    return df, X, y, feature_columns


def _save_group_metrics_csv(results, path: Path) -> None:
    rows = []
    for r in results:
        for g, m in r.group_metrics.items():
            row = m.to_dict()
            row["attribute"] = r.attribute_name
            rows.append(row)
    pd.DataFrame(rows).to_csv(path, index=False)


def _save_fairness_metrics_csv(results, path: Path) -> None:
    rows = []
    for r in results:
        for g, m in r.pairwise_metrics.items():
            rows.append({
                "attribute": r.attribute_name, "group": g, "reference_group": m.reference_group,
                "n_group": m.n_group, "n_reference": m.n_reference,
                "spd": m.statistical_parity_difference, "spd_ci_lower": m.spd_ci.ci_lower, "spd_ci_upper": m.spd_ci.ci_upper,
                "spd_significant": m.spd_ci.excludes_null,
                "dir": m.disparate_impact_ratio, "dir_ci_lower": m.dir_ci.ci_lower, "dir_ci_upper": m.dir_ci.ci_upper,
                "dir_significant": m.dir_ci.excludes_null,
                "eod": m.equal_opportunity_difference, "eod_ci_lower": m.eod_ci.ci_lower, "eod_ci_upper": m.eod_ci.ci_upper,
                "eod_significant": m.eod_ci.excludes_null,
                "aod": m.average_odds_difference, "aod_ci_lower": m.aod_ci.ci_lower, "aod_ci_upper": m.aod_ci.ci_upper,
                "aod_significant": m.aod_ci.excludes_null,
            })
    pd.DataFrame(rows).to_csv(path, index=False)


def main() -> int:
    config = load_config()
    configure_logging(
        logs_dir=config.paths.logs_dir, file_name=config.logging.file_name,
        level=config.logging.level, max_bytes=config.logging.max_bytes, backup_count=config.logging.backup_count,
    )
    logger = get_logger(__name__)
    logger.info("=== Module 5: Fairness Analysis ===")
    fairness_cfg = config.fairness_analysis

    with open(config.paths.feature_manifest_json, "r", encoding="utf-8") as fh:
        feature_manifest = json.load(fh)
    dataset_version = feature_manifest["dataset_version"]

    test_df, X_test, y_test, feature_columns = _load_test_set(config, feature_manifest)
    logger.info("Loaded test set: %s, %d features", X_test.shape, len(feature_columns))

    bundle_path = config.paths_m3.artifacts_m3_dir / f"{fairness_cfg.primary_model}_inference_bundle.joblib"
    bundle = joblib.load(bundle_path)
    threshold = bundle.threshold_decision.threshold
    y_proba = bundle.estimator.predict_proba(X_test)[:, 1]
    y_pred = (y_proba >= threshold).astype(int)
    logger.info("Primary model '%s' loaded (threshold=%.4f)", fairness_cfg.primary_model, threshold)
    logger.info("Fairlearn available for cross-validation: %s", is_fairlearn_available())

    artifacts_dir = config.paths_m5.artifacts_m5_dir
    reports_dir = config.paths_m5.reports_m5_dir
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for attr_cfg in fairness_cfg.protected_attributes:
        result = analyze_protected_attribute(
            y_test, y_pred, y_proba, test_df[attr_cfg.name], attr_cfg,
            fairness_cfg.statistics, fairness_cfg.fairness_thresholds,
            fairness_cfg.fairlearn_validation.enabled, fairness_cfg.fairlearn_validation.tolerance,
        )
        results.append(result)

        attr_dir = reports_dir / attr_cfg.name
        dpi = fairness_cfg.plots.dpi
        plot_selection_rate_comparison(result.group_metrics, attr_cfg.name, attr_dir / "selection_rate.png", dpi)
        plot_error_rate_comparison(result.group_metrics, attr_cfg.name, attr_dir / "error_rates.png", dpi)
        plot_group_confusion_matrices(result.group_metrics, attr_cfg.name, attr_dir / "confusion_matrices.png", dpi)

        group_labels_series = test_df[attr_cfg.name].astype(object).where(test_df[attr_cfg.name].notna(), "Missing")
        y_true_by_group = {g: y_test[group_labels_series == g] for g in group_labels_series.unique()}
        y_proba_by_group = {g: y_proba[group_labels_series == g] for g in group_labels_series.unique()}
        plot_roc_per_group(y_true_by_group, y_proba_by_group, attr_cfg.name, attr_dir / "roc_per_group.png", dpi)
        plot_pr_per_group(y_true_by_group, y_proba_by_group, attr_cfg.name, attr_dir / "pr_per_group.png", dpi)

        if result.pairwise_metrics:
            plot_fairness_metric_bars(result.pairwise_metrics, attr_cfg.name, attr_dir / "fairness_metrics_ci.png", dpi)
            plot_disparate_impact(
                result.pairwise_metrics, attr_cfg.name,
                fairness_cfg.fairness_thresholds.disparate_impact_low, fairness_cfg.fairness_thresholds.disparate_impact_high,
                attr_dir / "disparate_impact.png", dpi,
            )
        plot_fairness_dashboard(result.group_metrics, result.pairwise_metrics, attr_cfg.name, attr_dir / "dashboard.png", dpi)
        if attr_cfg.primary:
            # Top-level fairness_dashboard.png -- the primary attribute's dashboard,
            # duplicated at the report root since that's the single at-a-glance
            # artifact a reviewer expects to find without navigating into a subfolder.
            plot_fairness_dashboard(
                result.group_metrics, result.pairwise_metrics, attr_cfg.name, reports_dir / "fairness_dashboard.png", dpi
            )

    _save_group_metrics_csv(results, reports_dir / "group_metrics.csv")
    _save_fairness_metrics_csv(results, reports_dir / "fairness_metrics.csv")

    fairness_summary = {
        "model_analyzed": fairness_cfg.primary_model,
        "dataset_version": dataset_version,
        "attributes_analyzed": [r.attribute_name for r in results],
        "total_bias_findings": sum(len(r.bias_findings) for r in results),
        "critical_findings": sum(1 for r in results for f in r.bias_findings if f.severity == "critical"),
        "warning_findings": sum(1 for r in results for f in r.bias_findings if f.severity == "warning"),
    }
    with open(reports_dir / "fairness_summary.json", "w", encoding="utf-8") as fh:
        json.dump(fairness_summary, fh, indent=2)

    FairnessReportBuilder().build(fairness_cfg.primary_model, dataset_version, results, fairness_cfg, reports_dir)

    # --- Optional: Module 4 DP model comparison (primary attribute only) ---
    dp_comparison_result = None
    if fairness_cfg.include_dp_model_comparison:
        dp_model_path = config.paths_m4.artifacts_m4_dir / "dp_nn" / "model.keras"
        if dp_model_path.exists():
            logger.info("--- Optional: DP model (Module 4) fairness comparison on primary attribute ---")
            from tensorflow import keras
            dp_model = keras.models.load_model(dp_model_path)
            dp_proba = dp_model.predict(X_test.astype("float32"), verbose=0).ravel()
            # DP model's own optimized threshold, read from its persisted metadata (not re-derived here).
            with open(config.paths_m4.artifacts_m4_dir / "dp_nn" / "metadata.json", "r", encoding="utf-8") as fh:
                dp_metadata = json.load(fh)
            dp_threshold = 0.5  # DP model's threshold collapsed to 0.0 in Module 4 (see reports_m4); use 0.5 as a neutral reference point for this optional comparison
            dp_pred = (dp_proba >= dp_threshold).astype(int)
            primary_attr_cfg = fairness_cfg.primary_attribute()
            dp_comparison_result = analyze_protected_attribute(
                y_test, dp_pred, dp_proba, test_df[primary_attr_cfg.name], primary_attr_cfg,
                fairness_cfg.statistics, fairness_cfg.fairness_thresholds,
                False, fairness_cfg.fairlearn_validation.tolerance,  # no fairlearn re-check for the optional comparison
            )
            dp_dir = reports_dir / "dp_model_comparison"
            dp_dir.mkdir(parents=True, exist_ok=True)
            plot_fairness_dashboard(
                dp_comparison_result.group_metrics, dp_comparison_result.pairwise_metrics,
                f"{primary_attr_cfg.name} (DP model, threshold={dp_threshold})", dp_dir / "dashboard.png", fairness_cfg.plots.dpi,
            )
            with open(dp_dir / "dp_fairness_summary.json", "w", encoding="utf-8") as fh:
                json.dump({
                    "note": "OPTIONAL comparison only -- Module 4's DP model is not production-ready "
                            "(see reports_m4/investigation/); fairness metrics here are informational, "
                            f"not a certification. Evaluated at a neutral threshold={dp_threshold} since "
                            "the DP model's own optimized threshold collapsed to 0.0 (predict-all-positive).",
                    "group_metrics": {g: m.to_dict() for g, m in dp_comparison_result.group_metrics.items()},
                    "pairwise_metrics": {g: m.to_dict() for g, m in dp_comparison_result.pairwise_metrics.items()},
                }, fh, indent=2, default=str)
            logger.info("DP model comparison written to %s", dp_dir)
        else:
            logger.warning("Module 4 DP model artifact not found at %s -- skipping optional comparison.", dp_model_path)

    tracker = FairnessMLflowLogger(config.mlflow.tracking_uri, config.mlflow.experiment_name)
    run_id = tracker.log_fairness_run(fairness_cfg.primary_model, dataset_version, results, reports_dir)

    print(f"Fairness analysis complete for model '{fairness_cfg.primary_model}'.")
    print(f"Attributes analyzed: {[r.attribute_name for r in results]}")
    print(f"Total bias findings: {fairness_summary['total_bias_findings']} "
          f"({fairness_summary['critical_findings']} critical, {fairness_summary['warning_findings']} warning)")
    print(f"MLflow run: {run_id}")
    if dp_comparison_result:
        print("Optional DP model comparison generated (see reports_m5/dp_model_comparison/).")

    logger.info("Module 5 completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
