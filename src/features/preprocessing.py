"""Imputation, categorical encoding, scaling, and train/test splitting.

Design choices (each justified against the alternative considered):

* **Median imputation for numeric features, RobustScaler for scaling** —
  chosen over mean/StandardScaler because fraud transaction data is heavily
  right-skewed with extreme outliers (``TransactionAmt`` max ~31,937 vs
  median 68); mean and standard deviation are themselves distorted by those
  outliers, while median/IQR-based statistics are not.
* **Constant "missing" category + one-hot for low-cardinality categoricals**
  — chosen over dropping missing rows (would discard ~46-59% of rows for
  columns like M1-M9) and over silently imputing a majority category (would
  destroy the "missingness is itself predictive" signal already captured
  separately by :class:`~src.features.engineering.MissingIndicatorEngineer`).
* **Time-aware (chronological) train/test split as the default** — chosen
  over a random/stratified split because a fraud model is deployed to score
  transactions that happen *after* training data was collected; a random
  split would let the model implicitly learn from "future" transactions
  when predicting "past" ones, which cannot happen in production and would
  overstate offline evaluation metrics. A stratified random split is still
  provided for comparison/ablation, not as the production default.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, RobustScaler

from src.features.column_roles import TARGET_COLUMN, TIME_COLUMN
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class SplitReport:
    """Records how the train/test split was performed, for audit and MLflow logging."""

    strategy: str
    train_rows: int
    test_rows: int
    train_fraud_rate: float
    test_fraud_rate: float
    train_time_range: Optional[tuple[float, float]] = None
    test_time_range: Optional[tuple[float, float]] = None

    def to_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(asdict(self), fh, indent=2)
        logger.info("Split report written to %s", path)


class TrainTestSplitter:
    """Time-aware (default) or stratified-random train/test splitting."""

    def __init__(self, test_size: float = 0.2, random_state: int = 42) -> None:
        self.test_size = test_size
        self.random_state = random_state

    def time_aware_split(
        self, df: pd.DataFrame, time_col: str = TIME_COLUMN, target_col: str = TARGET_COLUMN
    ) -> tuple[pd.DataFrame, pd.DataFrame, SplitReport]:
        ordered = df.sort_values(time_col)
        split_idx = int(len(ordered) * (1 - self.test_size))
        train_df = ordered.iloc[:split_idx]
        test_df = ordered.iloc[split_idx:]
        report = SplitReport(
            strategy="time_aware",
            train_rows=len(train_df),
            test_rows=len(test_df),
            train_fraud_rate=float(train_df[target_col].mean()),
            test_fraud_rate=float(test_df[target_col].mean()),
            train_time_range=(float(train_df[time_col].min()), float(train_df[time_col].max())),
            test_time_range=(float(test_df[time_col].min()), float(test_df[time_col].max())),
        )
        logger.info(
            "Time-aware split: train=%d (fraud=%.4f) test=%d (fraud=%.4f)",
            report.train_rows, report.train_fraud_rate, report.test_rows, report.test_fraud_rate,
        )
        return train_df, test_df, report

    def stratified_split(
        self, df: pd.DataFrame, target_col: str = TARGET_COLUMN
    ) -> tuple[pd.DataFrame, pd.DataFrame, SplitReport]:
        train_df, test_df = train_test_split(
            df, test_size=self.test_size, stratify=df[target_col], random_state=self.random_state
        )
        report = SplitReport(
            strategy="stratified_random",
            train_rows=len(train_df),
            test_rows=len(test_df),
            train_fraud_rate=float(train_df[target_col].mean()),
            test_fraud_rate=float(test_df[target_col].mean()),
        )
        logger.info(
            "Stratified split: train=%d (fraud=%.4f) test=%d (fraud=%.4f)",
            report.train_rows, report.train_fraud_rate, report.test_rows, report.test_fraud_rate,
        )
        return train_df, test_df, report


def build_preprocessing_pipeline(
    numeric_features: list[str], categorical_features: list[str]
) -> ColumnTransformer:
    """Builds the imputation+scaling+encoding ColumnTransformer.

    Kept as a plain factory function (not a class) since it returns a
    standard, introspectable scikit-learn object that downstream code
    (Module 3 model training, MLflow artifact logging) can pickle, inspect,
    and reuse directly without depending on a project-specific wrapper type.
    """
    numeric_pipeline = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", RobustScaler()),
    ])
    categorical_pipeline = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
        ("encoder", OneHotEncoder(handle_unknown="ignore")),
    ])
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_features),
            ("categorical", categorical_pipeline, categorical_features),
        ],
        remainder="drop",
    )


def transform_to_dataframe(
    fitted_column_transformer: ColumnTransformer, X: pd.DataFrame, index: Optional[pd.Index] = None
) -> pd.DataFrame:
    """Applies a fitted ColumnTransformer and reconstructs a named DataFrame.

    scikit-learn's ColumnTransformer returns a bare numpy/sparse array;
    reconstructing column names via ``get_feature_names_out`` keeps every
    downstream artifact (model coefficients, SHAP plots, feature importance
    reports) human-readable instead of ``x0, x1, x2, ...``.
    """
    transformed = fitted_column_transformer.transform(X)
    if hasattr(transformed, "toarray"):
        transformed = transformed.toarray()
    feature_names = fitted_column_transformer.get_feature_names_out()
    return pd.DataFrame(transformed, columns=feature_names, index=index if index is not None else X.index)
