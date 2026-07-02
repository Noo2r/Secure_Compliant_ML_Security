import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from src.features.engineering import TimeFeatureEngineer, TransactionAmountFeatureEngineer
from src.features.preprocessing import build_preprocessing_pipeline
from src.features.selection import SelectedColumnsTransformer
from src.models.inference_bundle import InferenceBundle
from src.models.threshold import ThresholdDecision


def _build_fitted_bundle(tmp_path) -> tuple[InferenceBundle, pd.DataFrame]:
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
    from src.features.preprocessing import transform_to_dataframe
    processed = transform_to_dataframe(preprocessing_pipeline, selected)

    estimator = LogisticRegression().fit(processed.to_numpy(), engineered["isFraud"].to_numpy())
    threshold_decision = ThresholdDecision(
        strategy="max_f1", threshold=0.5, precision_at_threshold=0.5, recall_at_threshold=0.5, f1_at_threshold=0.5
    )
    bundle = InferenceBundle(
        model_name="logistic_regression",
        engineering_pipeline=engineering_pipeline,
        column_selector=column_selector,
        preprocessing_pipeline=preprocessing_pipeline,
        estimator=estimator,
        threshold_decision=threshold_decision,
        dataset_version="test-version",
    )
    return bundle, raw_df


def test_inference_bundle_predicts_directly_from_raw_data(tmp_path) -> None:
    bundle, raw_df = _build_fitted_bundle(tmp_path)
    proba = bundle.predict_proba(raw_df)
    assert proba.shape == (len(raw_df),)
    assert ((proba >= 0) & (proba <= 1)).all()
    predictions = bundle.predict(raw_df)
    assert set(np.unique(predictions)).issubset({0, 1})


def test_inference_bundle_survives_joblib_round_trip(tmp_path) -> None:
    bundle, raw_df = _build_fitted_bundle(tmp_path)
    path = tmp_path / "bundle.joblib"
    bundle.save(path)
    assert path.exists()

    reloaded = InferenceBundle.load(path)
    original_proba = bundle.predict_proba(raw_df)
    reloaded_proba = reloaded.predict_proba(raw_df)
    np.testing.assert_allclose(original_proba, reloaded_proba)
    assert reloaded.model_name == "logistic_regression"
    assert reloaded.dataset_version == "test-version"
