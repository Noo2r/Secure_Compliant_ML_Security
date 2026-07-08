"""
Loads the trained fraud-detection model produced in Milestone 2.

If no trained artifact is present yet (e.g. during infra bring-up before
Nour El-Din's model file is handed off), a deterministic placeholder scorer
is used so the rest of the security pipeline (auth, rate limiting, logging,
Key Vault wiring) can be built, tested, and pen-tested independently of the
ML deliverable. Swap in the real .joblib/.pkl file and this module will pick
it up automatically — no other code changes required.

Once the real artifact IS present, it deserializes to an
`src.models.inference_bundle.InferenceBundle` (see that module for the full
contract) rather than a bare scikit-learn-style estimator: it expects a raw
ML-ready pandas DataFrame (not an ndarray) in `predict_proba`, and it carries
its own tuned decision threshold rather than the conventional 0.5 — both
detected and handled explicitly below, since silently assuming the generic
`.predict_proba(ndarray)` / 0.5-threshold contract would either crash or
silently mis-threshold every real prediction.
"""
import logging
import os
from typing import Any

import numpy as np
import pandas as pd
import joblib

from app.core.config import get_settings

logger = logging.getLogger("fraud_api.model")


class _PlaceholderModel:
    """Rule-of-thumb stand-in used only until the real model is deployed."""

    version = "placeholder-0.1"

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        # Very naive heuristic: larger, unusual-looking amounts score higher.
        amt = X[:, 0]
        score = np.clip(amt / 5000.0, 0, 1)
        return np.column_stack([1 - score, score])


class ModelService:
    def __init__(self):
        settings = get_settings()
        self.model: Any
        self.version: str
        # An InferenceBundle is distinguished from the placeholder (or any
        # generic estimator) by carrying its own tuned decision threshold --
        # a reliable, attribute-based check that doesn't require importing
        # src.models.inference_bundle here (keeps this module usable even if
        # that package isn't on the path yet during infra bring-up).
        self.is_real_bundle: bool

        if os.path.exists(settings.MODEL_PATH):
            self.model = joblib.load(settings.MODEL_PATH)
            self.is_real_bundle = hasattr(self.model, "threshold_decision")
            if self.is_real_bundle:
                self.version = f"{self.model.model_name}@{self.model.dataset_version}"
            else:
                self.version = getattr(self.model, "version", "1.0")
            logger.info(
                "Loaded trained model from %s (real_bundle=%s, version=%s)",
                settings.MODEL_PATH, self.is_real_bundle, self.version,
            )
        else:
            logger.warning(
                "No trained model artifact found at %s — using placeholder scorer. "
                "Replace before production go-live.",
                settings.MODEL_PATH,
            )
            self.model = _PlaceholderModel()
            self.is_real_bundle = False
            self.version = self.model.version

    def predict(self, ml_ready_frame: pd.DataFrame) -> tuple[bool, float]:
        if self.is_real_bundle:
            # InferenceBundle.predict_proba() runs the raw frame through the
            # full Module 2 engineering/selection/preprocessing chain before
            # scoring, and returns one probability per row.
            proba = float(self.model.predict_proba(ml_ready_frame)[0])
            threshold = self.model.threshold_decision.threshold
            return bool(proba >= threshold), proba

        # Placeholder path — unchanged from Ali's original infra-bring-up
        # scorer: a bare ndarray with the amount in column 0, fixed 0.5
        # threshold. Adapted here only to accept the same DataFrame shape
        # every caller now passes, without touching _PlaceholderModel itself.
        amount_only = np.array([[float(ml_ready_frame["TransactionAmt"].iloc[0])]])
        proba = float(self.model.predict_proba(amount_only)[0][1])
        return bool(proba >= 0.5), proba


_model_service: ModelService | None = None


def get_model_service() -> ModelService:
    global _model_service
    if _model_service is None:
        _model_service = ModelService()
    return _model_service
