"""Verifies the full engineering -> selection -> preprocessing pipeline can be
persisted with joblib and reloaded to produce identical output -- this is
the concrete guarantee Module 3+ and any future deployment rely on: the
exact transformation fit here must be reproducible from disk, not just
valid within the lifetime of the process that fit it.
"""

from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from src.features.dataset_utils import extract_metadata_frame
from src.features.engineering import TimeFeatureEngineer, TransactionAmountFeatureEngineer
from src.features.preprocessing import build_preprocessing_pipeline, transform_to_dataframe
from src.features.selection import SelectedColumnsTransformer


def _toy_dataset(n: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    return pd.DataFrame({
        "TransactionID": range(n),
        "TransactionDT": np.arange(n) * 3600,
        "isFraud": rng.binomial(1, 0.2, size=n),
        "TransactionAmt": rng.normal(50, 10, size=n),
        "card6": rng.choice(["debit", "credit"], size=n),
    })


def test_full_pipeline_survives_joblib_round_trip(tmp_path) -> None:
    train_df = _toy_dataset(60)
    test_df = _toy_dataset(20)

    engineering_pipeline = Pipeline(steps=[
        ("time_features", TimeFeatureEngineer()),
        ("amount_features", TransactionAmountFeatureEngineer()),
    ])
    engineering_pipeline.fit(train_df)
    train_engineered = engineering_pipeline.transform(train_df)
    test_engineered = engineering_pipeline.transform(test_df)

    metadata_columns = ["TransactionID", "card6"]
    train_metadata = extract_metadata_frame(train_engineered, metadata_columns)
    assert list(train_metadata.columns) == metadata_columns

    selected_features = ["TransactionAmt", "TransactionAmt_log", "transaction_hour"]
    column_selector = SelectedColumnsTransformer(columns_to_keep=tuple(selected_features))
    column_selector.fit(train_engineered)
    train_selected = column_selector.transform(train_engineered)
    test_selected = column_selector.transform(test_engineered)

    preprocessing_pipeline = build_preprocessing_pipeline(
        numeric_features=selected_features, categorical_features=[]
    )
    preprocessing_pipeline.fit(train_selected)

    full_pipeline = Pipeline(steps=[
        ("engineering", engineering_pipeline),
        ("column_selection", column_selector),
        ("preprocessing", preprocessing_pipeline),
    ])

    expected = transform_to_dataframe(preprocessing_pipeline, test_selected).to_numpy()
    composed_before_dump = full_pipeline.transform(test_df)
    assert np.allclose(composed_before_dump, expected)

    # Metadata must never appear in the model-input pipeline's output.
    assert not any("TransactionID" in name for name in preprocessing_pipeline.get_feature_names_out())

    artifact_path = tmp_path / "full_inference_pipeline.joblib"
    joblib.dump(full_pipeline, artifact_path)
    reloaded_pipeline = joblib.load(artifact_path)

    composed_after_reload = reloaded_pipeline.transform(test_df)
    assert np.allclose(composed_after_reload, expected)
    assert np.allclose(composed_after_reload, composed_before_dump)


def test_persisted_engineering_pipeline_alone_round_trips(tmp_path) -> None:
    train_df = _toy_dataset(30)
    pipeline = Pipeline(steps=[("time_features", TimeFeatureEngineer())])
    pipeline.fit(train_df)
    expected = pipeline.transform(train_df)

    path = tmp_path / "engineering_pipeline.joblib"
    joblib.dump(pipeline, path)
    reloaded = joblib.load(path)

    pd.testing.assert_frame_equal(reloaded.transform(train_df), expected)
