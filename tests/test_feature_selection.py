import numpy as np
import pandas as pd
import pytest

from src.features.selection import FeatureSelectionComparator, SelectedColumnsTransformer

_TARGET = "isFraud"


def test_selected_columns_transformer_keeps_only_requested_columns() -> None:
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4], "c": [5, 6]})
    transformer = SelectedColumnsTransformer(columns_to_keep=("a", "c"))
    transformer.fit(df)
    out = transformer.transform(df)
    assert list(out.columns) == ["a", "c"]


def test_selected_columns_transformer_raises_on_missing_column_at_fit() -> None:
    df = pd.DataFrame({"a": [1, 2]})
    transformer = SelectedColumnsTransformer(columns_to_keep=("a", "does_not_exist"))
    with pytest.raises(ValueError, match="does_not_exist"):
        transformer.fit(df)


@pytest.fixture()
def synthetic_df() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    n = 2000
    y = rng.binomial(1, 0.2, size=n)
    informative = y * 5 + rng.normal(0, 1, size=n)  # strongly correlated with target
    noise = rng.normal(0, 1, size=n)  # pure noise, unrelated to target
    redundant_copy = informative * 2 + rng.normal(0, 0.01, size=n)  # near-duplicate of `informative`
    constant = np.ones(n)  # near-zero variance
    return pd.DataFrame({
        _TARGET: y,
        "informative": informative,
        "noise": noise,
        "redundant_copy": redundant_copy,
        "constant": constant,
    })


def test_near_zero_variance_column_is_dropped(synthetic_df: pd.DataFrame) -> None:
    comparator = FeatureSelectionComparator(ranking_sample_size=500, top_k_final_features=3)
    result = comparator.compare(
        synthetic_df, _TARGET, ["informative", "noise", "redundant_copy", "constant"]
    )
    assert "constant" in result.near_zero_variance_dropped


def test_correlation_redundancy_drops_one_of_the_correlated_pair(synthetic_df: pd.DataFrame) -> None:
    comparator = FeatureSelectionComparator(ranking_sample_size=500, top_k_final_features=3)
    result = comparator.compare(
        synthetic_df, _TARGET, ["informative", "noise", "redundant_copy", "constant"]
    )
    dropped = set(result.correlation_redundancy_dropped)
    # Exactly one of the redundant pair should be dropped, not both, not neither.
    assert len(dropped & {"informative", "redundant_copy"}) == 1


def test_informative_feature_outranks_noise(synthetic_df: pd.DataFrame) -> None:
    comparator = FeatureSelectionComparator(ranking_sample_size=500, top_k_final_features=3)
    result = comparator.compare(
        synthetic_df, _TARGET, ["informative", "noise", "redundant_copy", "constant"]
    )
    table = result.comparison_table.set_index("feature")
    assert table.loc["informative", "mutual_info_score"] > table.loc["noise", "mutual_info_score"]
    assert table.loc["informative", "importance_score"] > table.loc["noise", "importance_score"]


def test_selected_features_excludes_dropped_columns(synthetic_df: pd.DataFrame) -> None:
    comparator = FeatureSelectionComparator(ranking_sample_size=500, top_k_final_features=3)
    result = comparator.compare(
        synthetic_df, _TARGET, ["informative", "noise", "redundant_copy", "constant"]
    )
    assert "constant" not in result.selected_features
    assert "informative" in result.selected_features


def test_save_writes_csv_and_json(tmp_path, synthetic_df: pd.DataFrame) -> None:
    comparator = FeatureSelectionComparator(ranking_sample_size=500, top_k_final_features=3)
    result = comparator.compare(
        synthetic_df, _TARGET, ["informative", "noise", "redundant_copy", "constant"]
    )
    table_path = tmp_path / "comparison.csv"
    summary_path = tmp_path / "summary.json"
    result.save(table_path, summary_path)
    assert table_path.exists()
    assert summary_path.exists()
