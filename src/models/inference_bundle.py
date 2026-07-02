"""Self-contained, single-artifact inference pipeline for one trained model.

Bundles every fitted stage a raw ML-ready transaction needs to pass through
to reach a final fraud/not-fraud decision: Module 2's feature-engineering
pipeline, its feature-selection outcome, its preprocessing pipeline, this
model's trained estimator, and this model's optimized decision threshold.
Persisting one :class:`InferenceBundle` per candidate model with
``joblib`` means loading a single file is sufficient for inference --
nothing needs to be refit or rebuilt, and there is no risk of pairing a
model with the wrong preprocessing version.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from src.features.preprocessing import transform_to_dataframe
from src.models.threshold import ThresholdDecision
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class InferenceBundle:
    """Complete raw-input-to-decision pipeline for one trained fraud model.

    Parameters
    ----------
    model_name:
        Candidate model identifier (e.g. ``"xgboost"``), for traceability.
    engineering_pipeline, column_selector, preprocessing_pipeline:
        Module 2's fitted stages (identical across every candidate model --
        loaded once from ``artifacts_m2/`` and reused, not refit per model).
    estimator:
        This model's trained classifier (sklearn/XGBoost/LightGBM API, or
        :class:`~src.models.keras_wrapper.KerasClassifierWrapper` for the NN).
    threshold_decision:
        This model's optimized decision threshold and the metrics at that
        threshold, from :func:`src.models.threshold.optimize_threshold`.
    dataset_version:
        Module 2's dataset version string, carried through for audit
        traceability of exactly which data version trained this model.
    """

    model_name: str
    engineering_pipeline: Pipeline
    column_selector: Any
    preprocessing_pipeline: Any
    estimator: Any
    threshold_decision: ThresholdDecision
    dataset_version: str

    def predict_proba(self, raw_ml_ready_df: pd.DataFrame) -> np.ndarray:
        """Returns the positive-class (fraud) probability for each row.

        ``raw_ml_ready_df`` is a Module-1-style ML-ready frame (encrypted/PII
        columns already excluded, but otherwise untouched raw-ish data) --
        exactly the same shape of input the Module 2 pipeline was fit on.
        """
        engineered = self.engineering_pipeline.transform(raw_ml_ready_df)
        selected = self.column_selector.transform(engineered)
        processed = transform_to_dataframe(self.preprocessing_pipeline, selected)
        return self.estimator.predict_proba(processed.to_numpy())[:, 1]

    def predict(self, raw_ml_ready_df: pd.DataFrame) -> np.ndarray:
        """Binary fraud decision using this bundle's own optimized threshold."""
        proba = self.predict_proba(raw_ml_ready_df)
        return (proba >= self.threshold_decision.threshold).astype(int)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        logger.info("Persisted complete InferenceBundle for '%s' to %s", self.model_name, path)

    @staticmethod
    def load(path: Path) -> "InferenceBundle":
        return joblib.load(path)
