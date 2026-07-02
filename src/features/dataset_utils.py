"""Bridges Module 1's secured dataset output into Module 2's ML-ready frame."""

from __future__ import annotations

import pandas as pd

from src.data.classification_registry import DataClassificationRegistry
from src.utils.logger import get_logger

logger = get_logger(__name__)


def build_ml_ready_frame(df: pd.DataFrame, registry: DataClassificationRegistry) -> pd.DataFrame:
    """Drops encrypted/PII columns from Module 1's secured dataset.

    This is the single integration point between Module 1 (data security)
    and Module 2 (feature engineering): every downstream Module 2 component
    operates on this function's output, never on the raw secured dataset
    directly, so encrypted/PII columns can never accidentally leak into a
    model feature regardless of which Module 2 component runs next.
    """
    blocklist = registry.feature_blocklist()
    to_drop = [c for c in blocklist if c in df.columns]
    if to_drop:
        logger.info(
            "Dropping %d encrypted/PII columns before feature engineering: %s", len(to_drop), to_drop
        )
    return df.drop(columns=to_drop)


def extract_metadata_frame(df: pd.DataFrame, metadata_columns: list[str]) -> pd.DataFrame:
    """Extracts non-feature metadata columns (e.g. ``TransactionID``, fairness
    sensitive attributes) unmodified, preserving the original index so the
    result can be realigned with the processed feature matrix by index.

    These columns are carried through the pipeline in parallel with, but
    structurally outside of, the model feature matrix: they are never
    passed through imputation/scaling/encoding and never appear in the ``X``
    handed to ``model.fit()``. Kept separate deliberately, so no future
    change to the preprocessing pipeline can accidentally leak an identifier
    or sensitive attribute into model training.
    """
    present = [c for c in metadata_columns if c in df.columns]
    missing = [c for c in metadata_columns if c not in df.columns]
    if missing:
        logger.warning("Configured metadata columns not found in dataframe, skipping: %s", missing)
    return df[present].copy()
