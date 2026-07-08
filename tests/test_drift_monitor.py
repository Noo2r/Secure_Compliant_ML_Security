"""Tests for drift_monitor.py (Milestone 5, Youssef Tarek).

Covers the pure, deterministic logic -- threshold classification and the
real-vs-synthetic column-name resolution -- without running a full Evidently
report or needing network access. The column-resolution tests are a direct
regression test for a real bug found while integrating this module: it
originally matched selected-feature names against the real processed CSVs'
column names literally, but those are ColumnTransformer output columns
(`numeric__{name}` / one-hot-expanded `categorical__{name}_{value}`), so the
literal match found only 3 of ~150 selected features until this was fixed.
"""
import json

import pandas as pd
import pytest

from drift_monitor import _resolve_monitored_columns, _save_drift_status_json


def test_status_is_ok_when_drift_share_below_warning_threshold(tmp_path) -> None:
    summary = {"drift_share": 0.05, "dataset_drift": False, "n_drifted": 2, "n_features": 40}
    status = _save_drift_status_json(summary, tmp_path / "ref.csv", tmp_path / "cur.csv", tmp_path, synthetic=False)
    assert status == "ok"


def test_status_is_warning_between_thresholds(tmp_path) -> None:
    summary = {"drift_share": 0.15, "dataset_drift": True, "n_drifted": 6, "n_features": 40}
    status = _save_drift_status_json(summary, tmp_path / "ref.csv", tmp_path / "cur.csv", tmp_path, synthetic=False)
    assert status == "warning"


def test_status_is_critical_at_or_above_critical_threshold(tmp_path) -> None:
    summary = {"drift_share": 0.20, "dataset_drift": True, "n_drifted": 8, "n_features": 40}
    status = _save_drift_status_json(summary, tmp_path / "ref.csv", tmp_path / "cur.csv", tmp_path, synthetic=False)
    assert status == "critical"


def test_status_json_is_written_with_expected_fields(tmp_path) -> None:
    summary = {"drift_share": 0.5, "dataset_drift": False, "n_drifted": 1, "n_features": 2}
    _save_drift_status_json(summary, tmp_path / "ref.csv", tmp_path / "cur.csv", tmp_path, synthetic=True)

    payload = json.loads((tmp_path / "drift_status.json").read_text())
    assert payload["overall_status"] == "critical"
    assert payload["synthetic_data_used"] is True
    assert payload["action_required"] is True
    assert payload["n_drifted_features"] == 1
    assert payload["n_monitored_features"] == 2


def test_resolve_monitored_columns_matches_real_columntransformer_prefixes() -> None:
    """The real bug: literal names don't match the real processed CSV's
    `numeric__`/`categorical__`-prefixed, one-hot-expanded columns."""
    reference_df = pd.DataFrame({
        "numeric__TransactionAmt": [1.0, 2.0],
        "numeric__card1_amt_mean": [1.0, 2.0],
        "categorical__ProductCD_W": [1, 0],
        "categorical__ProductCD_H": [0, 1],
        "categorical__card6_debit": [1, 0],
        "categorical__card6_credit": [0, 1],
        "isFraud": [0, 1],
    })
    current_df = reference_df.copy()

    num_cols, cat_cols = _resolve_monitored_columns(
        reference_df, current_df,
        selected_num=["TransactionAmt", "card1_amt_mean", "not_a_real_feature"],
        selected_cat=["ProductCD", "card6"],
    )

    assert num_cols == ["numeric__TransactionAmt", "numeric__card1_amt_mean"]
    assert set(cat_cols) == {
        "categorical__ProductCD_W", "categorical__ProductCD_H",
        "categorical__card6_debit", "categorical__card6_credit",
    }


def test_resolve_monitored_columns_falls_back_to_bare_names_for_synthetic_data() -> None:
    """The synthetic-data path uses unprefixed column names directly."""
    df = pd.DataFrame({"TransactionAmt": [1.0], "ProductCD": ["W"], "isFraud": [0]})

    num_cols, cat_cols = _resolve_monitored_columns(
        df, df.copy(), selected_num=["TransactionAmt"], selected_cat=["ProductCD"],
    )

    assert num_cols == ["TransactionAmt"]
    assert cat_cols == ["ProductCD"]
