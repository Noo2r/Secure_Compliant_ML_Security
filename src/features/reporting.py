"""Generates the Module 2 feature engineering documentation and summary statistics.

Produces a single markdown report assembled from *actual runtime results*
(the real column diff, the real selection comparison table, the real split
statistics) rather than static prose, so the report always reflects what the
pipeline actually did on the most recent run — required for Farida's
Milestone 4 audit trail and for reproducibility.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data.secure_data_loader import DatasetManifest
from src.features.eda import DatasetProfile
from src.features.preprocessing import SplitReport
from src.features.selection import FeatureSelectionResult
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Justifications keyed by engineered-column-name prefix/exact-match, surfaced
# in the generated report next to each feature actually present in the run.
_FEATURE_JUSTIFICATIONS: dict[str, str] = {
    "transaction_hour": "Fraud rate ~3x higher at 07:00-09:00 (reference clock) than daily baseline (EDA).",
    "transaction_day_of_week": "Captures weekly seasonality in transaction/fraud volume.",
    "TransactionAmt_log": "Corrects heavy right-skew (median 68 vs max ~31,937) for linear/NN model stability.",
    "TransactionAmt_decimal": "Standard fraud-analytics feature; modest empirical association only (51.7% vs 52.9% zero-cents by class) -- retained as a candidate, final inclusion decided by feature selection.",
    "email_domain_match": "Fraud rate 9.65% (domains match) vs 2.21% (domains differ) -- one of the strongest engineered signals found (EDA).",
    "P_emaildomain_grouped": "Per-domain fraud rate ranges 0.7%-9.4%; grouping to top domains preserves signal while capping cardinality.",
    "R_emaildomain_grouped": "Same rationale as P_emaildomain_grouped, recipient side.",
    "card1_txn_count": "Classic velocity feature; EDA showed only weak/non-monotonic signal alone -- retained as a selection candidate.",
    "card1_amt_mean": "Per-card historical spending baseline for deviation scoring.",
    "card1_amt_std": "Per-card spending variability for deviation scoring.",
    "card1_amt_zscore": "How unusual this transaction's amount is relative to this card's own history.",
    "_was_missing": "Missingness itself is predictive (e.g. DeviceType missing correlates with ~4x lower fraud rate); flags one indicator per unique missingness pattern to avoid ~100+ near-duplicate columns.",
}


def _justification_for(column: str) -> str:
    if column in _FEATURE_JUSTIFICATIONS:
        return _FEATURE_JUSTIFICATIONS[column]
    for key, text in _FEATURE_JUSTIFICATIONS.items():
        if key.startswith("_") and column.endswith(key):
            return text
    return "Domain-standard fraud-detection feature; see src/features/engineering.py docstring."


class FeatureEngineeringReportBuilder:
    """Assembles the Module 2 markdown report from real pipeline outputs."""

    def build(
        self,
        dataset_manifest: DatasetManifest,
        profile: DatasetProfile,
        original_columns: list[str],
        engineered_columns: list[str],
        selection_result: FeatureSelectionResult,
        split_report: SplitReport,
        output_path: Path,
        metadata_columns: list[str] | None = None,
        artifact_paths: dict[str, str] | None = None,
    ) -> None:
        metadata_columns = metadata_columns or []
        artifact_paths = artifact_paths or {}
        newly_engineered = [c for c in engineered_columns if c not in original_columns]
        removed_by_selection = sorted(
            set(selection_result.near_zero_variance_dropped) | set(selection_result.correlation_redundancy_dropped)
        )

        lines = [
            "# Module 2 — Feature Engineering & Selection Report",
            "",
            "## 1. Upstream dataset (Module 1)",
            f"- Dataset version: `{dataset_manifest.dataset_version}` (mode: {dataset_manifest.mode})",
            f"- Rows: {dataset_manifest.row_count:,}",
            f"- Encrypted/PII columns excluded before engineering: {list(dataset_manifest.encrypted_columns)}",
            "",
            "## 2. Pre-engineering profile (see eda_profile_report.md for full detail)",
            f"- ML-ready columns analyzed: {profile.column_count}",
            f"- Numeric: {len(profile.numeric_columns)}, Categorical: {len(profile.categorical_columns)}, "
            f"ID-like: {len(profile.id_like_columns)}",
            f"- Columns with >5% missing: {len(profile.high_missingness_columns)}",
            f"- Redundant (|corr|>0.95) column pairs found: {len(profile.redundant_column_pairs)}",
            "",
            "## 3. Engineered features",
            "",
            "| Feature | Justification |",
            "|---|---|",
        ]
        for col in newly_engineered:
            lines.append(f"| {col} | {_justification_for(col)} |")

        lines += [
            "",
            "## 4. Feature selection method comparison",
            "",
            selection_result.method_justification,
            "",
            f"- Candidates considered: {len(selection_result.comparison_table)}",
            f"- Dropped (near-zero variance): {len(selection_result.near_zero_variance_dropped)}",
            f"- Dropped (correlation redundancy): {len(selection_result.correlation_redundancy_dropped)}",
            f"- Final selected features: {len(selection_result.selected_features)}",
            "",
            "### Removed features (with reason)",
            "",
            "| Feature | Reason |",
            "|---|---|",
        ]
        for col in removed_by_selection:
            reason = (
                "Near-zero variance (>99.9% single value)"
                if col in selection_result.near_zero_variance_dropped
                else "Correlation redundancy (|corr|>0.95 with a stronger-target-correlated feature)"
            )
            lines.append(f"| {col} | {reason} |")

        lines += [
            "",
            "### Top 20 selected features by consensus rank (MI + embedded importance)",
            "",
            "| Feature | MI score | MI rank | Importance score | Importance rank |",
            "|---|---|---|---|---|",
        ]
        top_selected = selection_result.comparison_table[
            selection_result.comparison_table["feature"].isin(selection_result.selected_features)
        ].sort_values(["mutual_info_rank", "importance_rank"]).head(20)
        for _, row in top_selected.iterrows():
            lines.append(
                f"| {row['feature']} | {row['mutual_info_score']:.5f} | {int(row['mutual_info_rank'])} | "
                f"{row['importance_score']:.5f} | {int(row['importance_rank'])} |"
            )

        lines += [
            "",
            "## 5. Train/test split",
            f"- Strategy: {split_report.strategy}",
            f"- Train rows: {split_report.train_rows:,} (fraud rate {split_report.train_fraud_rate:.4f})",
            f"- Test rows: {split_report.test_rows:,} (fraud rate {split_report.test_fraud_rate:.4f})",
        ]
        if split_report.train_time_range:
            lines.append(f"- Train time range: {split_report.train_time_range}")
        if split_report.test_time_range:
            lines.append(f"- Test time range: {split_report.test_time_range}")

        lines += [
            "",
            "## 6. Metadata columns (preserved, non-feature)",
            "",
            "These columns are present in the processed train/test CSVs for traceability, "
            "auditing, explainability, and fairness slicing. They are extracted BEFORE feature "
            "selection/preprocessing and never pass through imputation, scaling, encoding, or "
            "selection -- **they must never be included in the X passed to model.fit()/predict()**.",
            "",
            "| Column | Role |",
            "|---|---|",
        ]
        for col in metadata_columns:
            role = "Row identifier (traceability/audit)" if col == "TransactionID" else "Fairness sensitive/proxy attribute"
            lines.append(f"| {col} | {role} |")

        lines += [
            "",
            "## 7. Persisted inference artifacts (joblib)",
            "",
            "Every fitted stage is persisted so Module 3+ (and later deployment) can apply the "
            "identical transformation to new data without refitting on this dataset again.",
            "",
            "| Artifact | Contents |",
            "|---|---|",
            f"| `{artifact_paths.get('engineering_pipeline', 'engineering_pipeline.joblib')}` | Fitted feature-engineering Pipeline (time/amount features, email grouping, frequency encoders, card velocity stats, missing-indicator patterns) |",
            f"| `{artifact_paths.get('column_selector', 'column_selector.joblib')}` | Fitted `SelectedColumnsTransformer` embodying the feature-selection decision |",
            f"| `{artifact_paths.get('preprocessing_pipeline', 'preprocessing_pipeline.joblib')}` | Fitted `ColumnTransformer` (imputers, `RobustScaler`, `OneHotEncoder`) |",
            f"| `{artifact_paths.get('full_inference_pipeline', 'full_inference_pipeline.joblib')}` | Single composed Pipeline chaining all three stages above -- the one artifact Module 3/deployment should load for end-to-end raw-to-model-ready transformation |",
            f"| `{artifact_paths.get('feature_selector', 'feature_selector.joblib')}` | The `FeatureSelectionComparator` configuration used (thresholds, sample size, seed) for exact reproducibility |",
        ]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        logger.info("Feature engineering report written to %s", output_path)
