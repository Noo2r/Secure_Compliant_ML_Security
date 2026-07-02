import numpy as np
import pandas as pd

from src.features.eda import DatasetProfiler


def test_profiler_classifies_columns_and_computes_target_correlation() -> None:
    rng = np.random.default_rng(1)
    n = 300
    y = rng.binomial(1, 0.3, size=n)
    df = pd.DataFrame({
        "TransactionID": range(n),
        "isFraud": y,
        "TransactionDT": np.arange(n) * 10,
        "TransactionAmt": rng.normal(50, 5, size=n),
        "card1": rng.integers(1, 5000, size=n),  # id-like, high cardinality
        "ProductCD": rng.choice(["W", "C", "R"], size=n),  # low-cardinality categorical
        "V1": y * 3 + rng.normal(0, 1, size=n),  # correlated with target
    })
    profiler = DatasetProfiler()
    profile = profiler.profile(df)

    assert "card1" in profile.id_like_columns
    assert "ProductCD" in profile.categorical_columns
    assert "V1" in profile.numeric_columns
    assert "TransactionAmt" in profile.numeric_columns
    assert set(profile.target_distribution.keys()) == {"0", "1"}
    assert abs(profile.correlation_with_target["V1"]) > abs(profile.correlation_with_target["TransactionAmt"])


def test_profiler_detects_redundant_correlated_pairs() -> None:
    rng = np.random.default_rng(2)
    n = 300
    base = rng.normal(0, 1, size=n)
    df = pd.DataFrame({
        "isFraud": rng.binomial(1, 0.2, size=n),
        "V1": base,
        "V2": base * 2 + rng.normal(0, 0.001, size=n),  # near-perfectly correlated with V1
        "V3": rng.normal(0, 1, size=n),  # independent
    })
    profiler = DatasetProfiler()
    profile = profiler.profile(df)
    pairs = {(a, b) for a, b, _ in profile.redundant_column_pairs}
    assert ("V1", "V2") in pairs or ("V2", "V1") in pairs


def test_profile_json_and_markdown_round_trip(tmp_path) -> None:
    df = pd.DataFrame({
        "isFraud": [0, 1, 0, 1],
        "TransactionAmt": [10.0, 20.0, 30.0, 40.0],
    })
    profile = DatasetProfiler().profile(df)
    json_path = tmp_path / "profile.json"
    md_path = tmp_path / "profile.md"
    profile.to_json(json_path)
    profile.to_markdown(md_path)
    assert json_path.exists()
    assert md_path.exists()
    assert "Module 2" in md_path.read_text(encoding="utf-8")
