"""Feature selection: compares multiple approaches and picks a final feature set.

Four approaches are implemented and compared, each with a distinct blind
spot the others cover:

1. **Near-zero-variance filter** (heuristic, not raw ``VarianceThreshold``):
   flags columns where one value dominates >99.9% of rows — scale-invariant,
   unlike a raw variance cutoff, which would unfairly penalize
   small-magnitude columns purely for being small-scale.
2. **Correlation-redundancy filter**: among numeric column pairs with
   |corr| > 0.95 (dominated by the Vesta "V" block — 124 of 339 V columns
   had such a partner per the EDA pass), keeps whichever column of the pair
   correlates more strongly with the target, drops the other.
3. **Mutual information (filter method)**: model-agnostic, captures
   non-linear but single-feature relationships; computed on a stratified
   sample for tractability at ~450 candidate columns x 590K rows.
4. **Embedded tree importance**: a fast Random Forest fit on the same
   sample; captures interactions and non-linearities MI alone would miss,
   at the cost of a mild bias toward high-cardinality/continuous features.

**Recursive Feature Elimination (wrapper method) was deliberately excluded.**
RFE requires refitting a model once per eliminated feature (or per step),
which at ~450 candidate columns is computationally prohibitive for every
model family in this milestone's comparison (Module 3), and it would not
add information beyond what the embedded importance method above already
provides from the same estimator family — a filter+embedded combination is
the standard, defensible choice for high-dimensional fraud-detection
pipelines where feature-selection decisions must also be auditable
(Farida's Milestone 4 compliance review) and explainable (SHAP, Module 6).

The final feature set is a **consensus** of MI and importance rankings
(rather than either alone), reducing the risk of over-trusting a single
method's blind spot on a feature set materially informing a fraud-risk
model in a regulated domain.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import mutual_info_classif
from sklearn.model_selection import train_test_split

from src.utils.logger import get_logger

logger = get_logger(__name__)


class SelectedColumnsTransformer(BaseEstimator, TransformerMixin):
    """Applies a feature-selection outcome as a reusable, persistable transformer.

    :class:`FeatureSelectionComparator` produces a *decision* (which columns
    to keep); this class turns that decision into an ordinary fitted
    scikit-learn transformer so it can be composed into the same
    ``Pipeline`` as the engineering and preprocessing stages and persisted
    with ``joblib`` alongside them — the selection outcome is then just as
    reproducible and inference-ready as any other pipeline stage, rather
    than being a one-off script variable that only exists for the duration
    of a single run.
    """

    def __init__(self, columns_to_keep: tuple[str, ...]) -> None:
        self.columns_to_keep = columns_to_keep

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> "SelectedColumnsTransformer":
        missing = [c for c in self.columns_to_keep if c not in X.columns]
        if missing:
            raise ValueError(
                f"SelectedColumnsTransformer expected columns not present in input: {missing}"
            )
        # Trailing-underscore marker so sklearn's check_is_fitted (used by
        # Pipeline.transform()) recognizes this transformer as fitted -- see
        # TimeFeatureEngineer's docstring for why this matters even here.
        self.is_fitted_ = True
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        return X[list(self.columns_to_keep)].copy()


@dataclass(frozen=True)
class FeatureSelectionResult:
    comparison_table: pd.DataFrame  # per-feature scores/ranks from every method
    selected_features: tuple[str, ...]
    near_zero_variance_dropped: tuple[str, ...]
    correlation_redundancy_dropped: tuple[str, ...]
    method_justification: str

    def save(self, table_path: Path, summary_json_path: Path) -> None:
        table_path.parent.mkdir(parents=True, exist_ok=True)
        self.comparison_table.to_csv(table_path, index=False)
        summary = {
            "selected_feature_count": len(self.selected_features),
            "selected_features": list(self.selected_features),
            "near_zero_variance_dropped": list(self.near_zero_variance_dropped),
            "correlation_redundancy_dropped": list(self.correlation_redundancy_dropped),
            "method_justification": self.method_justification,
        }
        with open(summary_json_path, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)
        logger.info("Feature selection comparison saved to %s / %s", table_path, summary_json_path)


class FeatureSelectionComparator:
    """Runs all four selection approaches and produces a consensus feature set.

    Parameters
    ----------
    near_zero_variance_freq_threshold:
        A column is flagged near-zero-variance if its single most frequent
        value accounts for more than this fraction of non-null rows.
    correlation_redundancy_threshold:
        Absolute correlation above which two numeric columns are considered
        redundant.
    ranking_sample_size:
        Row count for the stratified sample used by the (comparatively
        expensive) mutual-information and embedded-importance methods. The
        near-zero-variance and correlation filters run on the full dataset
        since they are cheap vectorized operations.
    top_k_final_features:
        Number of features retained in the final consensus selection.
    """

    def __init__(
        self,
        near_zero_variance_freq_threshold: float = 0.999,
        correlation_redundancy_threshold: float = 0.95,
        ranking_sample_size: int = 50_000,
        top_k_final_features: int = 150,
        random_state: int = 42,
    ) -> None:
        self.near_zero_variance_freq_threshold = near_zero_variance_freq_threshold
        self.correlation_redundancy_threshold = correlation_redundancy_threshold
        self.ranking_sample_size = ranking_sample_size
        self.top_k_final_features = top_k_final_features
        self.random_state = random_state

    def compare(self, df: pd.DataFrame, target_column: str, candidate_columns: list[str]) -> FeatureSelectionResult:
        logger.info("Running feature selection comparison over %d candidate columns", len(candidate_columns))

        nzv_dropped = self._near_zero_variance_dropped(df, candidate_columns)
        survivors_after_nzv = [c for c in candidate_columns if c not in nzv_dropped]

        corr_dropped = self._correlation_redundancy_dropped(df, survivors_after_nzv, target_column)
        survivors_after_corr = [c for c in survivors_after_nzv if c not in corr_dropped]

        ranking_df, y_sample = self._stratified_ranking_sample(df, target_column, survivors_after_corr)
        mi_scores = self._mutual_information_scores(ranking_df, y_sample)
        importance_scores = self._embedded_importance_scores(ranking_df, y_sample)

        comparison_table = self._build_comparison_table(
            candidate_columns, nzv_dropped, corr_dropped, mi_scores, importance_scores
        )

        selected = self._consensus_selection(comparison_table)

        justification = (
            f"Consensus of mutual information + embedded Random Forest importance over "
            f"{len(survivors_after_corr)} candidates surviving near-zero-variance "
            f"({len(nzv_dropped)} dropped) and correlation-redundancy "
            f"({len(corr_dropped)} dropped) filters. Top {self.top_k_final_features} by "
            f"averaged normalized rank retained. RFE excluded as computationally infeasible "
            f"at this dimensionality and redundant with the embedded method already used."
        )

        result = FeatureSelectionResult(
            comparison_table=comparison_table,
            selected_features=tuple(selected),
            near_zero_variance_dropped=tuple(nzv_dropped),
            correlation_redundancy_dropped=tuple(corr_dropped),
            method_justification=justification,
        )
        logger.info(
            "Feature selection complete: %d selected / %d candidates", len(selected), len(candidate_columns)
        )
        return result

    # ------------------------------------------------------------------
    # 1. Near-zero-variance filter
    # ------------------------------------------------------------------
    def _near_zero_variance_dropped(self, df: pd.DataFrame, columns: list[str]) -> list[str]:
        dropped = []
        for col in columns:
            series = df[col].dropna()
            if series.empty:
                dropped.append(col)
                continue
            top_freq_ratio = series.value_counts(normalize=True).iloc[0]
            if top_freq_ratio > self.near_zero_variance_freq_threshold:
                dropped.append(col)
        logger.info("Near-zero-variance filter dropped %d columns", len(dropped))
        return dropped

    # ------------------------------------------------------------------
    # 2. Correlation-redundancy filter (numeric columns only)
    # ------------------------------------------------------------------
    def _correlation_redundancy_dropped(
        self, df: pd.DataFrame, columns: list[str], target_column: str
    ) -> list[str]:
        numeric_cols = [c for c in columns if pd.api.types.is_numeric_dtype(df[c])]
        if len(numeric_cols) < 2:
            return []

        corr_with_target = df[numeric_cols + [target_column]].corr(numeric_only=True)[target_column].abs()
        corr_matrix = df[numeric_cols].corr(numeric_only=True).abs()
        upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape, dtype=bool), k=1))

        redundant_pairs = []
        for col in upper.columns:
            partners = upper[col][upper[col] > self.correlation_redundancy_threshold]
            for partner, value in partners.items():
                redundant_pairs.append((col, partner, value))
        redundant_pairs.sort(key=lambda t: t[2], reverse=True)

        dropped: set[str] = set()
        for col_a, col_b, _ in redundant_pairs:
            if col_a in dropped or col_b in dropped:
                continue
            # Keep whichever of the pair correlates more strongly with the target.
            score_a = corr_with_target.get(col_a, 0.0)
            score_b = corr_with_target.get(col_b, 0.0)
            dropped.add(col_b if score_a >= score_b else col_a)

        logger.info(
            "Correlation-redundancy filter dropped %d columns from %d redundant pairs",
            len(dropped), len(redundant_pairs),
        )
        return list(dropped)

    # ------------------------------------------------------------------
    # Shared ranking-sample preparation for MI / embedded importance
    # ------------------------------------------------------------------
    def _stratified_ranking_sample(
        self, df: pd.DataFrame, target_column: str, columns: list[str]
    ) -> tuple[pd.DataFrame, pd.Series]:
        n = min(self.ranking_sample_size, len(df))
        if n < len(df):
            sample_df, _ = train_test_split(
                df, train_size=n, stratify=df[target_column], random_state=self.random_state
            )
        else:
            sample_df = df

        X = sample_df[columns].copy()
        y = sample_df[target_column].copy()

        # Ranking-only encoding: ordinal-encode object columns, median-impute
        # numeric NaNs. This is intentionally simpler than the production
        # preprocessing pipeline (Module 2's preprocessing.py) -- it exists
        # solely to make every candidate column consumable by MI/RandomForest
        # for ranking purposes, not to produce model-ready features.
        for col in X.columns:
            if not pd.api.types.is_numeric_dtype(X[col]):
                X[col] = pd.factorize(X[col])[0]
            else:
                median = X[col].median()
                X[col] = X[col].fillna(median if pd.notna(median) else 0)
        return X, y

    # ------------------------------------------------------------------
    # 3. Mutual information (filter method)
    # ------------------------------------------------------------------
    def _mutual_information_scores(self, X: pd.DataFrame, y: pd.Series) -> pd.Series:
        scores = mutual_info_classif(X, y, random_state=self.random_state)
        logger.info("Mutual information computed for %d features", len(X.columns))
        return pd.Series(scores, index=X.columns)

    # ------------------------------------------------------------------
    # 4. Embedded importance (Random Forest)
    # ------------------------------------------------------------------
    def _embedded_importance_scores(self, X: pd.DataFrame, y: pd.Series) -> pd.Series:
        model = RandomForestClassifier(
            n_estimators=200, max_depth=8, class_weight="balanced",
            n_jobs=-1, random_state=self.random_state,
        )
        model.fit(X, y)
        logger.info("Embedded Random Forest importance computed for %d features", len(X.columns))
        return pd.Series(model.feature_importances_, index=X.columns)

    # ------------------------------------------------------------------
    # Comparison table + consensus selection
    # ------------------------------------------------------------------
    @staticmethod
    def _build_comparison_table(
        all_candidates: list[str],
        nzv_dropped: list[str],
        corr_dropped: list[str],
        mi_scores: pd.Series,
        importance_scores: pd.Series,
    ) -> pd.DataFrame:
        rows = []
        for col in all_candidates:
            rows.append({
                "feature": col,
                "near_zero_variance_dropped": col in nzv_dropped,
                "correlation_redundancy_dropped": col in corr_dropped,
                "mutual_info_score": mi_scores.get(col, np.nan),
                "importance_score": importance_scores.get(col, np.nan),
            })
        table = pd.DataFrame(rows)
        table["mutual_info_rank"] = table["mutual_info_score"].rank(ascending=False, method="min")
        table["importance_rank"] = table["importance_score"].rank(ascending=False, method="min")
        return table

    def _consensus_selection(self, table: pd.DataFrame) -> list[str]:
        eligible = table[
            ~table["near_zero_variance_dropped"] & ~table["correlation_redundancy_dropped"]
        ].copy()
        eligible = eligible.dropna(subset=["mutual_info_rank", "importance_rank"])
        eligible["consensus_rank"] = eligible[["mutual_info_rank", "importance_rank"]].mean(axis=1)
        eligible = eligible.sort_values("consensus_rank")
        return eligible["feature"].head(self.top_k_final_features).tolist()
