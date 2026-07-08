"""Tests for app.models.model_loader.ModelService's dispatch between the real
InferenceBundle contract and the Milestone 3 placeholder scorer.

Mirrors tests/test_inference_bundle.py's `_build_fitted_bundle` pattern: a
tiny, fast-to-fit real InferenceBundle rather than a mock, so this exercises
the actual joblib round-trip and the actual predict_proba()/threshold
contract ModelService depends on.
"""
import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.core.config import get_settings
from app.models.model_loader import ModelService
from src.features.engineering import TimeFeatureEngineer, TransactionAmountFeatureEngineer
from src.features.preprocessing import build_preprocessing_pipeline, transform_to_dataframe
from src.features.selection import SelectedColumnsTransformer
from src.models.inference_bundle import InferenceBundle
from src.models.threshold import ThresholdDecision


def _build_fitted_bundle(threshold: float) -> InferenceBundle:
    rng = np.random.default_rng(3)
    n = 200
    raw_df = pd.DataFrame({
        "TransactionID": range(n),
        "TransactionDT": np.arange(n) * 3600,
        "isFraud": rng.binomial(1, 0.2, size=n),
        "TransactionAmt": rng.normal(50, 15, size=n),
    })

    engineering_pipeline = Pipeline(steps=[
        ("time_features", TimeFeatureEngineer()),
        ("amount_features", TransactionAmountFeatureEngineer()),
    ])
    engineering_pipeline.fit(raw_df)
    engineered = engineering_pipeline.transform(raw_df)

    selected_features = ["TransactionAmt", "TransactionAmt_log", "transaction_hour"]
    column_selector = SelectedColumnsTransformer(columns_to_keep=tuple(selected_features))
    column_selector.fit(engineered)
    selected = column_selector.transform(engineered)

    preprocessing_pipeline = build_preprocessing_pipeline(numeric_features=selected_features, categorical_features=[])
    preprocessing_pipeline.fit(selected)
    processed = transform_to_dataframe(preprocessing_pipeline, selected)

    estimator = LogisticRegression().fit(processed.to_numpy(), engineered["isFraud"].to_numpy())
    threshold_decision = ThresholdDecision(
        strategy="max_f1", threshold=threshold,
        precision_at_threshold=0.5, recall_at_threshold=0.5, f1_at_threshold=0.5,
    )
    return InferenceBundle(
        model_name="logistic_regression",
        engineering_pipeline=engineering_pipeline,
        column_selector=column_selector,
        preprocessing_pipeline=preprocessing_pipeline,
        estimator=estimator,
        threshold_decision=threshold_decision,
        dataset_version="test-version",
    )


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_model_service_loads_real_bundle_and_reports_its_version(tmp_path, monkeypatch) -> None:
    bundle = _build_fitted_bundle(threshold=0.5)
    bundle_path = tmp_path / "bundle.joblib"
    bundle.save(bundle_path)
    monkeypatch.setenv("MODEL_PATH", str(bundle_path))

    service = ModelService()

    assert service.is_real_bundle is True
    assert service.version == "logistic_regression@test-version"


def test_model_service_uses_the_bundles_own_threshold_not_a_hardcoded_half(tmp_path, monkeypatch) -> None:
    # A deliberately high threshold (0.9): any probability between 0.5 and
    # 0.9 must be classified as NOT fraud. The old hardcoded `>= 0.5` logic
    # would have gotten this wrong for exactly this range -- this is the
    # regression test for that fix (see model_loader.py's module docstring).
    bundle = _build_fitted_bundle(threshold=0.9)
    bundle_path = tmp_path / "bundle.joblib"
    bundle.save(bundle_path)
    monkeypatch.setenv("MODEL_PATH", str(bundle_path))

    service = ModelService()
    raw_row = pd.DataFrame([{
        "TransactionID": 999, "TransactionDT": 3600, "TransactionAmt": 50.0,
    }])

    is_fraud, probability = service.predict(raw_row)

    assert 0.0 <= probability <= 1.0
    # is_fraud must follow the bundle's 0.9 threshold, not a hardcoded 0.5.
    assert is_fraud == (probability >= 0.9)


def test_model_service_falls_back_to_placeholder_when_artifact_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MODEL_PATH", str(tmp_path / "does_not_exist.joblib"))

    service = ModelService()

    assert service.is_real_bundle is False
    assert service.version == "placeholder-0.1"

    raw_row = pd.DataFrame([{"TransactionAmt": 4000.0}])
    is_fraud, probability = service.predict(raw_row)
    assert probability == pytest.approx(0.8, abs=1e-9)  # 4000 / 5000, per _PlaceholderModel
    assert is_fraud is True
