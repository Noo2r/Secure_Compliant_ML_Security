"""Pre-engineering dataset analysis ("Analyze the dataset before engineering
any features").

This module profiles the Module 1 ML-ready frame (secured dataset with the
encrypted-column blocklist already removed) and produces the evidence used
to justify every decision made in :mod:`src.features.engineering` and
:mod:`src.features.selection` — column roles, missingness patterns,
target correlation, and redundancy among the highly collinear Vesta
("V") engineered-feature block. Nothing downstream should assume a feature
is useful or a column should be dropped without this profile backing it up.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.features.column_roles import (
    AMOUNT_COLUMN,
    HIGH_CARDINALITY_CATEGORICAL_FREQUENCY,
    HIGH_CARDINALITY_CATEGORICAL_GROUPED,
    ID_LIKE_HIGH_CARDINALITY_NUMERIC,
    LOW_CARDINALITY_CATEGORICAL,
    MERGE_KEY_COLUMN,
    TARGET_COLUMN,
    TIME_COLUMN,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

_CORRELATION_REDUNDANCY_THRESHOLD = 0.95
_NON_FEATURE_COLUMNS = (MERGE_KEY_COLUMN, TARGET_COLUMN, TIME_COLUMN)


@dataclass(frozen=True)
class DatasetProfile:
    """Structured profiling output consumed by engineering/selection/reports."""

    row_count: int
    column_count: int
    numeric_columns: tuple[str, ...]
    categorical_columns: tuple[str, ...]
    id_like_columns: tuple[str, ...]
    target_distribution: dict[str, float]
    missingness_pct: dict[str, float]
    high_missingness_columns: tuple[str, ...]  # >5% missing
    cardinality: dict[str, int]
    correlation_with_target: dict[str, float]
    redundant_column_pairs: tuple[tuple[str, str, float], ...]  # (col_a, col_b, |corr|)

    def to_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(asdict(self), fh, indent=2, default=str)
        logger.info("Dataset profile JSON written to %s", path)

    def to_markdown(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        top_target_corr = sorted(
            self.correlation_with_target.items(), key=lambda kv: abs(kv[1]), reverse=True
        )[:20]
        lines = [
            "# Module 2 — Pre-Engineering Dataset Profile",
            "",
            f"- Rows: {self.row_count:,}",
            f"- Columns (ML-ready, post encrypted-column blocklist): {self.column_count}",
            f"- Numeric columns: {len(self.numeric_columns)}",
            f"- Categorical columns: {len(self.categorical_columns)}",
            f"- ID-like high-cardinality numeric columns: {list(self.id_like_columns)}",
            f"- Target distribution: {self.target_distribution}",
            f"- Columns with >5% missing: {len(self.high_missingness_columns)}",
            "",
            "## Top 20 numeric columns by |correlation| with isFraud",
            "",
            "| Column | Correlation |",
            "|---|---|",
        ]
        lines += [f"| {c} | {v:.4f} |" for c, v in top_target_corr]
        lines += [
            "",
            f"## Redundant column pairs (|corr| > {_CORRELATION_REDUNDANCY_THRESHOLD})",
            "",
            f"Found {len(self.redundant_column_pairs)} pairs. First 20 shown:",
            "",
            "| Column A | Column B | |corr| |",
            "|---|---|---|",
        ]
        lines += [f"| {a} | {b} | {v:.4f} |" for a, b, v in self.redundant_column_pairs[:20]]
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        logger.info("Dataset profile markdown report written to %s", path)


class DatasetProfiler:
    """Profiles the ML-ready frame to inform feature engineering/selection."""

    def profile(self, df: pd.DataFrame) -> DatasetProfile:
        logger.info("Profiling dataset: shape=%s", df.shape)

        numeric_columns, categorical_columns, id_like_columns = self._classify_columns(df)

        target_distribution = (
            df[TARGET_COLUMN].value_counts(normalize=True).to_dict()
            if TARGET_COLUMN in df.columns else {}
        )

        missingness_pct = (df.isnull().mean() * 100).to_dict()
        high_missingness_columns = tuple(
            col for col, pct in missingness_pct.items() if pct > 5.0
        )

        cardinality = {
            col: int(df[col].nunique(dropna=True))
            for col in categorical_columns + id_like_columns
            if col in df.columns
        }

        correlation_with_target = self._correlation_with_target(df, numeric_columns)
        redundant_pairs = self._redundant_pairs(df, numeric_columns)

        profile = DatasetProfile(
            row_count=len(df),
            column_count=df.shape[1],
            numeric_columns=tuple(numeric_columns),
            categorical_columns=tuple(categorical_columns),
            id_like_columns=tuple(id_like_columns),
            target_distribution={str(k): float(v) for k, v in target_distribution.items()},
            missingness_pct={k: float(v) for k, v in missingness_pct.items()},
            high_missingness_columns=high_missingness_columns,
            cardinality=cardinality,
            correlation_with_target=correlation_with_target,
            redundant_column_pairs=redundant_pairs,
        )
        logger.info(
            "Profile complete: %d numeric, %d categorical, %d id-like, %d redundant pairs found",
            len(numeric_columns), len(categorical_columns), len(id_like_columns), len(redundant_pairs),
        )
        return profile

    @staticmethod
    def _classify_columns(df: pd.DataFrame) -> tuple[list[str], list[str], list[str]]:
        """Split columns into numeric / categorical / id-like using domain
        knowledge from column_roles.py first, falling back to dtype for any
        column not explicitly classified (e.g. the V/C/D blocks).
        """
        id_like = [c for c in ID_LIKE_HIGH_CARDINALITY_NUMERIC if c in df.columns]
        categorical = [
            c for c in (
                list(LOW_CARDINALITY_CATEGORICAL)
                + list(HIGH_CARDINALITY_CATEGORICAL_GROUPED)
                + list(HIGH_CARDINALITY_CATEGORICAL_FREQUENCY)
            )
            if c in df.columns
        ]
        explicitly_classified = set(id_like) | set(categorical) | set(_NON_FEATURE_COLUMNS)
        numeric = [
            c for c in df.columns
            if c not in explicitly_classified and pd.api.types.is_numeric_dtype(df[c])
        ]
        return numeric, categorical, id_like

    @staticmethod
    def _correlation_with_target(df: pd.DataFrame, numeric_columns: list[str]) -> dict[str, float]:
        if TARGET_COLUMN not in df.columns:
            return {}
        usable = [c for c in numeric_columns if c in df.columns]
        if not usable:
            return {}
        corr = df[usable + [TARGET_COLUMN]].corr(numeric_only=True)[TARGET_COLUMN].drop(TARGET_COLUMN)
        return {k: float(v) for k, v in corr.items() if not np.isnan(v)}

    @staticmethod
    def _redundant_pairs(
        df: pd.DataFrame, numeric_columns: list[str], threshold: float = _CORRELATION_REDUNDANCY_THRESHOLD
    ) -> tuple[tuple[str, str, float], ...]:
        """Find numeric column pairs exceeding the redundancy threshold.

        Restricted to numeric_columns (excludes id-like/target/time), which
        in practice is dominated by the V-block where redundancy is known to
        be high; this keeps the O(n^2) correlation matrix computation bounded.
        """
        usable = [c for c in numeric_columns if c in df.columns]
        if len(usable) < 2:
            return tuple()
        corr = df[usable].corr(numeric_only=True).abs()
        upper = corr.where(np.triu(np.ones(corr.shape, dtype=bool), k=1))
        pairs = []
        for col in upper.columns:
            partners = upper[col][upper[col] > threshold]
            for partner, value in partners.items():
                pairs.append((col, partner, float(value)))
        pairs.sort(key=lambda t: t[2], reverse=True)
        return tuple(pairs)
