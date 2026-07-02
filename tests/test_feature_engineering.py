import numpy as np
import pandas as pd
import pytest

from src.features.engineering import (
    CardVelocityFeatureEngineer,
    EmailDomainGrouper,
    FrequencyEncoder,
    MissingIndicatorEngineer,
    TimeFeatureEngineer,
    TransactionAmountFeatureEngineer,
)


def test_time_feature_engineer_derives_hour_and_day_of_week() -> None:
    df = pd.DataFrame({"TransactionDT": [0, 3600 * 9, 3600 * 25, 86400 * 8]})
    out = TimeFeatureEngineer().fit_transform(df)
    # 3600*25s = 90,000s = 1 day + 3600s -> hour 1, day_of_week 1
    assert out["transaction_hour"].tolist() == [0, 9, 1, 0]
    assert out["transaction_day_of_week"].tolist() == [0, 0, 1, 1]


def test_transaction_amount_feature_engineer_log_and_decimal() -> None:
    df = pd.DataFrame({"TransactionAmt": [10.0, 10.25, 0.0]})
    out = TransactionAmountFeatureEngineer().fit_transform(df)
    assert np.isclose(out["TransactionAmt_log"].iloc[0], np.log1p(10.0))
    assert np.isclose(out["TransactionAmt_decimal"].iloc[1], 0.25)
    assert np.isclose(out["TransactionAmt_decimal"].iloc[2], 0.0)


def test_email_domain_grouper_learns_top_n_from_train_only() -> None:
    train = pd.DataFrame({
        "P_emaildomain": ["gmail.com"] * 5 + ["yahoo.com"] * 3 + ["rare.com"],
        "R_emaildomain": ["gmail.com"] * 5 + ["yahoo.com"] * 3 + ["rare.com"],
    })
    test = pd.DataFrame({
        "P_emaildomain": ["gmail.com", "brandnew.com", None],
        "R_emaildomain": ["gmail.com", "other-brandnew.com", None],
    })
    grouper = EmailDomainGrouper(top_n=2)
    grouper.fit(train)
    out = grouper.transform(test)
    assert out["P_emaildomain_grouped"].tolist() == ["gmail.com", "other", "missing"]
    # A domain unseen in training must not spuriously match another unseen domain.
    assert out["email_domain_match"].tolist() == [1, 0, 0]


def test_frequency_encoder_replaces_column_with_train_frequency() -> None:
    train = pd.DataFrame({"card_id": ["A", "A", "A", "B", "B", "C"]})
    test = pd.DataFrame({"card_id": ["A", "B", "C", "unseen"]})
    encoder = FrequencyEncoder(columns=("card_id",))
    encoder.fit(train)
    out = encoder.transform(test)
    assert out["card_id"].tolist() == [3.0, 2.0, 1.0, 0.0]


def test_card_velocity_feature_engineer_uses_train_fallback_for_unseen_groups() -> None:
    train = pd.DataFrame({"card1": [1, 1, 2], "TransactionAmt": [100.0, 200.0, 50.0]})
    test = pd.DataFrame({"card1": [1, 999], "TransactionAmt": [150.0, 10.0]})
    engineer = CardVelocityFeatureEngineer(group_col="card1", amount_col="TransactionAmt")
    engineer.fit(train)
    out = engineer.transform(test)
    assert out.loc[0, "card1_txn_count"] == 2  # card1==1 seen twice in train
    # unseen card1==999 falls back to the global training mean, not NaN
    assert not np.isnan(out.loc[1, "card1_amt_mean"])
    assert out.loc[1, "card1_amt_mean"] == pytest.approx(train["TransactionAmt"].mean())


def test_missing_indicator_engineer_collapses_identical_missingness_patterns() -> None:
    # V1 and V2 share an identical null mask -> should collapse to one indicator.
    df = pd.DataFrame({
        "V1": [1.0, None, None, 4.0, None, None, None, None, None, None],
        "V2": [9.0, None, None, 8.0, None, None, None, None, None, None],
        "V3": [1.0] * 10,  # no missingness -> not eligible
    })
    engineer = MissingIndicatorEngineer(candidate_columns=("V1", "V2", "V3"), min_missing_pct=5.0)
    engineer.fit(df)
    out = engineer.transform(df)
    flag_cols = [c for c in out.columns if c.endswith("_was_missing")]
    assert len(flag_cols) == 1  # V1 and V2 collapsed into a single indicator
    assert "V3_was_missing" not in out.columns
