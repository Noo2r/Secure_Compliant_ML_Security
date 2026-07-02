"""Module 2 entrypoint: Feature Engineering & Feature Selection.

Run from the repository root:

    python scripts/run_module2.py

Pipeline order (chosen deliberately to prevent train/test leakage):

    1. Load Module 1's secured dataset + classification registry.
    2. Build the ML-ready frame (encrypted/PII columns dropped).
    3. Profile the dataset BEFORE any engineering (descriptive only; informs
       design, does not fit any leakage-sensitive statistic).
    4. Time-aware train/test split -- performed BEFORE any stateful
       transformer is fit, so every learned statistic below only ever sees
       the training fold.
    5. Fit feature engineering transformers on train, transform train+test.
    6. Extract metadata columns (TransactionID + fairness sensitive
       attributes) BEFORE feature selection/preprocessing -- these are
       carried through to the final output unmodified and are structurally
       outside the model feature matrix, never passed through selection,
       imputation, scaling, or encoding.
    7. Feature selection comparison -- run on the TRAIN fold only -- applied
       via a fitted, persistable SelectedColumnsTransformer.
    8. Fit the imputation/scaling/encoding pipeline on train, transform both.
    9. Persist every fitted stage (engineering, selection, preprocessing,
       and the composed end-to-end inference pipeline) with joblib, plus
       processed train/test matrices and full documentation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from src.config.config_loader import load_config
from src.data.classification_registry import DataClassificationRegistry
from src.data.secure_data_loader import SecureDatasetLoader
from src.features.column_roles import MERGE_KEY_COLUMN, TARGET_COLUMN, TIME_COLUMN
from src.features.dataset_utils import build_ml_ready_frame, extract_metadata_frame
from src.features.eda import DatasetProfiler
from src.features.engineering import (
    CardVelocityFeatureEngineer,
    EmailDomainGrouper,
    FrequencyEncoder,
    MissingIndicatorEngineer,
    TimeFeatureEngineer,
    TransactionAmountFeatureEngineer,
)
from src.features.preprocessing import (
    TrainTestSplitter,
    build_preprocessing_pipeline,
    transform_to_dataframe,
)
from src.features.reporting import FeatureEngineeringReportBuilder
from src.features.selection import FeatureSelectionComparator, SelectedColumnsTransformer
from src.utils.logger import configure_logging, get_logger

# Raw high-cardinality email domain columns are superseded by EmailDomainGrouper's
# *_grouped output and must not be offered to feature selection as-is (59/60
# raw categories would defeat the cardinality-capping purpose of grouping).
_SUPERSEDED_RAW_COLUMNS = ("P_emaildomain", "R_emaildomain")
_NEVER_FEATURE_COLUMNS = (MERGE_KEY_COLUMN, TARGET_COLUMN, TIME_COLUMN)


def main() -> int:
    config = load_config()
    configure_logging(
        logs_dir=config.paths.logs_dir,
        file_name=config.logging.file_name,
        level=config.logging.level,
        max_bytes=config.logging.max_bytes,
        backup_count=config.logging.backup_count,
    )
    logger = get_logger(__name__)
    logger.info("=== Module 2: Feature Engineering & Feature Selection ===")

    # --- Step 1-2: Module 1 integration ---
    registry = DataClassificationRegistry.from_csv(
        data_classification_csv=config.upstream_milestone1.data_classification_csv,
        data_lineage_csv=config.upstream_milestone1.data_lineage_csv,
    )
    loader = SecureDatasetLoader(config=config, classification_registry=registry)
    secured_df, dataset_manifest = loader.load()
    ml_df = build_ml_ready_frame(secured_df, registry)

    # --- Step 3: Pre-engineering profile ---
    profiler = DatasetProfiler()
    profile = profiler.profile(ml_df)
    profile.to_json(config.paths.reports_m2_dir / "eda_profile.json")
    profile.to_markdown(config.paths.reports_m2_dir / "eda_profile_report.md")

    # --- Step 4: Time-aware split BEFORE any stateful transformer is fit ---
    splitter = TrainTestSplitter(test_size=config.train_test_split.test_size)
    if config.train_test_split.strategy == "stratified_random":
        train_df, test_df, split_report = splitter.stratified_split(ml_df)
    else:
        train_df, test_df, split_report = splitter.time_aware_split(ml_df)
    split_report.to_json(config.paths.reports_m2_dir / "split_report.json")

    # --- Step 5: Feature engineering, fit on train only ---
    missing_indicator_candidates = tuple(
        c for c in ml_df.columns
        if c.startswith(("D", "id_", "V")) or c in ("DeviceType", "DeviceInfo", "P_emaildomain", "R_emaildomain")
    )
    engineering_pipeline = Pipeline(steps=[
        ("time_features", TimeFeatureEngineer()),
        ("amount_features", TransactionAmountFeatureEngineer()),
        ("email_domain_grouping", EmailDomainGrouper(top_n=config.feature_engineering.email_domain_top_n)),
        ("card_velocity", CardVelocityFeatureEngineer(group_col=config.feature_engineering.card_velocity_group_col)),
        ("frequency_encoding", FrequencyEncoder(columns=("id_30", "id_31", "id_33", "DeviceInfo"))),
        ("missing_indicators", MissingIndicatorEngineer(
            candidate_columns=missing_indicator_candidates,
            min_missing_pct=config.feature_engineering.missing_indicator_min_missing_pct,
        )),
    ])
    engineering_pipeline.fit(train_df)
    train_engineered = engineering_pipeline.transform(train_df)
    test_engineered = engineering_pipeline.transform(test_df)
    logger.info(
        "Engineering added %d new columns (train shape %s -> %s)",
        train_engineered.shape[1] - train_df.shape[1], train_df.shape, train_engineered.shape,
    )

    # --- Step 6: Extract metadata (never touches selection/preprocessing) ---
    metadata_columns = [c for c in config.metadata.preserved_columns if c in train_engineered.columns]
    train_metadata = extract_metadata_frame(train_engineered, metadata_columns)
    test_metadata = extract_metadata_frame(test_engineered, metadata_columns)
    logger.info(
        "Preserved %d metadata columns (never used for training): %s", len(metadata_columns), metadata_columns
    )

    # --- Step 7: Feature selection comparison, on TRAIN fold only ---
    candidate_columns = [
        c for c in train_engineered.columns
        if c not in _NEVER_FEATURE_COLUMNS and c not in _SUPERSEDED_RAW_COLUMNS
    ]
    selector = FeatureSelectionComparator(
        near_zero_variance_freq_threshold=config.feature_selection.near_zero_variance_freq_threshold,
        correlation_redundancy_threshold=config.feature_selection.correlation_redundancy_threshold,
        ranking_sample_size=config.feature_selection.ranking_sample_size,
        top_k_final_features=config.feature_selection.top_k_final_features,
        random_state=config.project.random_seed,
    )
    selection_result = selector.compare(train_engineered, TARGET_COLUMN, candidate_columns)
    selection_result.save(
        table_path=config.paths.reports_m2_dir / "feature_selection_comparison.csv",
        summary_json_path=config.paths.reports_m2_dir / "feature_selection_summary.json",
    )

    selected_features = list(selection_result.selected_features)
    categorical_selected = [
        c for c in selected_features
        if not pd.api.types.is_numeric_dtype(train_engineered[c])
    ]
    numeric_selected = [c for c in selected_features if c not in categorical_selected]

    # Feature selection outcome applied as a fitted, persistable transformer
    # (not a bare DataFrame slice) so it composes into the same Pipeline as
    # the engineering and preprocessing stages.
    column_selector = SelectedColumnsTransformer(columns_to_keep=tuple(selected_features))
    column_selector.fit(train_engineered)
    train_selected = column_selector.transform(train_engineered)
    test_selected = column_selector.transform(test_engineered)

    # --- Step 8: Preprocessing (impute/scale/encode), fit on train only ---
    preprocessing_pipeline = build_preprocessing_pipeline(numeric_selected, categorical_selected)
    preprocessing_pipeline.fit(train_selected)
    train_processed_features = transform_to_dataframe(preprocessing_pipeline, train_selected)
    test_processed_features = transform_to_dataframe(preprocessing_pipeline, test_selected)

    # --- Sanity check: the composed end-to-end pipeline must reproduce the
    # manually-chained result exactly, before it is trusted and persisted. ---
    full_inference_pipeline = Pipeline(steps=[
        ("engineering", engineering_pipeline),
        ("column_selection", column_selector),
        ("preprocessing", preprocessing_pipeline),
    ])
    composed_output = full_inference_pipeline.transform(test_df)
    manually_chained_output = test_processed_features.to_numpy()
    if not np.allclose(composed_output, manually_chained_output, equal_nan=True):
        raise RuntimeError(
            "Composed full_inference_pipeline output does not match the manually-chained "
            "pipeline output -- refusing to persist an inconsistent inference artifact."
        )
    logger.info("Composed full_inference_pipeline verified identical to the manually-chained pipeline.")

    # Metadata + processed features + target, realigned by index (never by
    # row position), then written out. Metadata columns are NEVER part of
    # numeric_selected/categorical_selected and therefore never reach
    # preprocessing_pipeline's imputer/scaler/encoder.
    train_processed = pd.concat([train_metadata, train_processed_features], axis=1)
    test_processed = pd.concat([test_metadata, test_processed_features], axis=1)
    train_processed[TARGET_COLUMN] = train_engineered[TARGET_COLUMN]
    test_processed[TARGET_COLUMN] = test_engineered[TARGET_COLUMN]

    # --- Step 9: Persist artifacts ---
    config.paths.processed_train_csv.parent.mkdir(parents=True, exist_ok=True)
    train_processed.to_csv(config.paths.processed_train_csv, index=False)
    test_processed.to_csv(config.paths.processed_test_csv, index=False)
    logger.info(
        "Processed train/test matrices written: train=%s test=%s",
        train_processed.shape, test_processed.shape,
    )

    artifacts_dir = config.paths.artifacts_m2_dir
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    artifact_paths = {
        "engineering_pipeline": artifacts_dir / "engineering_pipeline.joblib",
        "column_selector": artifacts_dir / "column_selector.joblib",
        "preprocessing_pipeline": artifacts_dir / "preprocessing_pipeline.joblib",
        "full_inference_pipeline": artifacts_dir / "full_inference_pipeline.joblib",
        "feature_selector": artifacts_dir / "feature_selector.joblib",
    }
    joblib.dump(engineering_pipeline, artifact_paths["engineering_pipeline"])
    joblib.dump(column_selector, artifact_paths["column_selector"])
    joblib.dump(preprocessing_pipeline, artifact_paths["preprocessing_pipeline"])
    joblib.dump(full_inference_pipeline, artifact_paths["full_inference_pipeline"])
    joblib.dump(selector, artifact_paths["feature_selector"])
    logger.info("Persisted %d fitted pipeline artifacts to %s", len(artifact_paths), artifacts_dir)

    feature_manifest = {
        "selected_features": selected_features,
        "numeric_features": numeric_selected,
        "categorical_features": categorical_selected,
        "metadata_columns": metadata_columns,
        "target_column": TARGET_COLUMN,
        "final_processed_column_count": train_processed.shape[1] - 1 - len(metadata_columns),  # model features only
        "dataset_version": dataset_manifest.dataset_version,
        "usage_notes": (
            "metadata_columns (e.g. TransactionID, fairness sensitive attributes) are present in "
            "the processed CSVs for traceability, auditing, explainability, and fairness slicing, "
            "but MUST NEVER be included in the X passed to model.fit()/predict() -- use only "
            "selected_features (equivalently: all columns except metadata_columns and target_column)."
        ),
        "artifact_paths": {k: str(v) for k, v in artifact_paths.items()},
    }
    with open(config.paths.feature_manifest_json, "w", encoding="utf-8") as fh:
        json.dump(feature_manifest, fh, indent=2)
    logger.info("Feature manifest written to %s", config.paths.feature_manifest_json)

    report_builder = FeatureEngineeringReportBuilder()
    report_builder.build(
        dataset_manifest=dataset_manifest,
        profile=profile,
        original_columns=list(ml_df.columns),
        engineered_columns=list(train_engineered.columns),
        selection_result=selection_result,
        split_report=split_report,
        output_path=config.paths.reports_m2_dir / "feature_engineering_report.md",
        metadata_columns=metadata_columns,
        artifact_paths={k: str(v) for k, v in artifact_paths.items()},
    )

    print(f"Selected {len(selected_features)} model features "
          f"({len(numeric_selected)} numeric, {len(categorical_selected)} categorical)")
    print(f"Metadata columns preserved (non-feature): {metadata_columns}")
    print(f"Train processed shape: {train_processed.shape}, Test processed shape: {test_processed.shape}")
    print(f"Split strategy: {split_report.strategy}, train fraud rate: {split_report.train_fraud_rate:.4f}, "
          f"test fraud rate: {split_report.test_fraud_rate:.4f}")
    print(f"Fitted pipeline artifacts persisted to: {artifacts_dir}")

    logger.info("Module 2 completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
