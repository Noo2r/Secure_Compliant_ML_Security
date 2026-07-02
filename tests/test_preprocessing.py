import numpy as np
import pandas as pd
import pytest

from src.features.preprocessing import (
    TrainTestSplitter,
    build_preprocessing_pipeline,
    transform_to_dataframe,
)


@pytest.fixture()
def toy_df() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    n = 200
    return pd.DataFrame({
        "TransactionID": range(n),
        "TransactionDT": np.arange(n) * 100,
        "isFraud": rng.binomial(1, 0.1, size=n),
        "amount": rng.normal(50, 10, size=n),
        "category": rng.choice(["A", "B", "C"], size=n),
    })


def test_time_aware_split_orders_train_strictly_before_test(toy_df: pd.DataFrame) -> None:
    splitter = TrainTestSplitter(test_size=0.2)
    train_df, test_df, report = splitter.time_aware_split(toy_df)
    assert train_df["TransactionDT"].max() <= test_df["TransactionDT"].min()
    assert report.strategy == "time_aware"
    assert report.train_rows + report.test_rows == len(toy_df)


def test_stratified_split_preserves_approximate_fraud_rate(toy_df: pd.DataFrame) -> None:
    splitter = TrainTestSplitter(test_size=0.25, random_state=42)
    train_df, test_df, report = splitter.stratified_split(toy_df)
    overall_rate = toy_df["isFraud"].mean()
    assert abs(report.train_fraud_rate - overall_rate) < 0.1
    assert abs(report.test_fraud_rate - overall_rate) < 0.1


def test_preprocessing_pipeline_imputes_scales_and_encodes(toy_df: pd.DataFrame) -> None:
    df = toy_df.copy()
    df.loc[0:5, "amount"] = np.nan  # introduce missing values to exercise imputation
    pipeline = build_preprocessing_pipeline(numeric_features=["amount"], categorical_features=["category"])
    pipeline.fit(df)
    out = transform_to_dataframe(pipeline, df)

    assert not out.isna().any().any()  # imputation removed all NaNs
    # One-hot encoding produced one column per category
    onehot_cols = [c for c in out.columns if c.startswith("categorical__category_")]
    assert len(onehot_cols) == 3


def test_preprocessing_pipeline_handles_unseen_category_at_transform_time(toy_df: pd.DataFrame) -> None:
    train_df = toy_df[toy_df["category"] != "C"]
    test_df = toy_df[toy_df["category"] == "C"]
    pipeline = build_preprocessing_pipeline(numeric_features=["amount"], categorical_features=["category"])
    pipeline.fit(train_df)
    # Must not raise even though "C" was never seen during fit.
    out = transform_to_dataframe(pipeline, test_df)
    assert len(out) == len(test_df)
