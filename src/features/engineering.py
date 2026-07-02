"""Feature engineering transformers for fraud detection.

Every transformer implements the scikit-learn ``fit``/``transform`` API so
they compose inside a single :class:`sklearn.pipeline.Pipeline` and — the
part that actually matters for a fraud model — any statistic they learn
(frequency tables, group aggregates, top-domain lists, missingness
signatures) is learned in ``fit`` on the training fold only and merely
*applied* in ``transform``. This is what prevents target/train-test leakage
when the pipeline is refit inside cross-validation or re-run at inference
time.

Every feature engineered here is backed by an empirical check performed
during the Module 2 EDA pass (see ``reports_m2/eda_profile_report.md`` and
the Module 2 approval discussion) rather than folklore about the IEEE-CIS
dataset:

* ``transaction_hour`` — fraud rate is ~3x higher at 07:00-09:00 (reference
  clock) than the daily baseline (~9-11% vs ~3%).
* ``email_domain_match`` — fraud rate is 9.65% when purchaser/recipient
  email domains match vs 2.21% when they don't (the opposite of the naive
  assumption that a domain match signals legitimacy — kept as an
  evidence-driven, not assumed, feature).
* ``P_emaildomain``/``R_emaildomain`` grouping — per-domain fraud rate
  ranges from 0.7% (att.net) to 9.4% (outlook.com); grouping to the top-N
  domains preserves this signal while capping cardinality.
* ``*_was_missing`` indicators — e.g. DeviceType missing correlates with an
  ~4x LOWER fraud rate (2.1% vs 8.0%) than DeviceType present, so
  missingness itself is predictive, not just a nuisance to impute away.
* ``TransactionAmt_decimal`` — a commonly cited fraud-analytics feature;
  empirically only a modest association was found in this dataset (51.7%
  vs 52.9% zero-cents rate by class), so it is engineered as a *candidate*
  and its survival is left to the Module 2 feature-selection stage rather
  than assumed important.
"""

from __future__ import annotations

import hashlib
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

from src.features.column_roles import AMOUNT_COLUMN, EMAIL_DOMAIN_TOP_N, TIME_COLUMN
from src.utils.logger import get_logger

logger = get_logger(__name__)

_SECONDS_PER_HOUR = 3600
_SECONDS_PER_DAY = 86400
_SECONDS_PER_WEEK = _SECONDS_PER_DAY * 7


class TimeFeatureEngineer(BaseEstimator, TransformerMixin):
    """Derives cyclical time-of-day/day-of-week features from ``TransactionDT``.

    ``TransactionDT`` is a seconds-elapsed-since-a-reference-point counter,
    not a wall-clock timestamp, but the reference point is a fixed anchor for
    the whole dataset, so ``TransactionDT modulo 1 day`` still recovers a
    consistent (if arbitrarily-offset) hour-of-day cycle — confirmed by the
    3x fraud-rate spike observed at specific modulo-hours during EDA.
    Stateless: no fit-time statistics are required. ``fit`` still sets
    ``is_fitted_`` -- scikit-learn's ``check_is_fitted`` (used internally by
    ``Pipeline.transform()``) looks for a trailing-underscore attribute to
    confirm an estimator was fit; without one, a composed ``Pipeline``
    containing this transformer would raise ``NotFittedError`` even after
    ``fit()`` ran successfully, which is exactly the failure this project's
    own pipeline-persistence tests caught.
    """

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> "TimeFeatureEngineer":
        self.is_fitted_ = True
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()
        if TIME_COLUMN not in X.columns:
            logger.warning("%s not present; skipping time feature engineering", TIME_COLUMN)
            return X
        X["transaction_hour"] = (X[TIME_COLUMN] // _SECONDS_PER_HOUR) % 24
        X["transaction_day_of_week"] = (X[TIME_COLUMN] // _SECONDS_PER_DAY) % 7
        return X


class TransactionAmountFeatureEngineer(BaseEstimator, TransformerMixin):
    """Derives log-scaled and decimal-cents features from ``TransactionAmt``.

    ``TransactionAmt_log`` (log1p) tames the heavy right skew (median 68 vs
    max ~31,937) that would otherwise dominate distance/gradient-based
    models (Logistic Regression, Neural Network). ``TransactionAmt_decimal``
    is retained as a candidate feature per the class docstring's honesty
    note about its modest empirical association. Stateless, but ``fit``
    still sets ``is_fitted_`` -- see :class:`TimeFeatureEngineer` docstring
    for why this is required even for a stateless transformer.
    """

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> "TransactionAmountFeatureEngineer":
        self.is_fitted_ = True
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()
        if AMOUNT_COLUMN not in X.columns:
            logger.warning("%s not present; skipping amount feature engineering", AMOUNT_COLUMN)
            return X
        X["TransactionAmt_log"] = np.log1p(X[AMOUNT_COLUMN])
        X["TransactionAmt_decimal"] = (X[AMOUNT_COLUMN] - np.floor(X[AMOUNT_COLUMN])).round(2)
        return X


class EmailDomainGrouper(BaseEstimator, TransformerMixin):
    """Groups high-cardinality email domain columns and derives a match flag.

    Learns the top-N most frequent domains per column from the training
    fold only (``fit``); at transform time, any domain outside that
    training-derived set collapses to ``"other"`` and missing values to
    ``"missing"``. This keeps the categories a downstream one-hot encoder
    sees fixed and leak-free, while preserving the strong per-domain fraud
    signal found during EDA. ``email_domain_match`` compares the *raw*
    (ungrouped) domains, since grouping both to "other" could otherwise
    create false matches between genuinely different rare domains.
    """

    def __init__(self, purchaser_col: str = "P_emaildomain", recipient_col: str = "R_emaildomain",
                 top_n: int = EMAIL_DOMAIN_TOP_N) -> None:
        self.purchaser_col = purchaser_col
        self.recipient_col = recipient_col
        self.top_n = top_n

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> "EmailDomainGrouper":
        self.top_domains_: dict[str, set[str]] = {}
        for col in (self.purchaser_col, self.recipient_col):
            if col in X.columns:
                self.top_domains_[col] = set(X[col].value_counts().head(self.top_n).index)
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()
        if self.purchaser_col in X.columns and self.recipient_col in X.columns:
            X["email_domain_match"] = (
                X[self.purchaser_col].notna()
                & (X[self.purchaser_col] == X[self.recipient_col])
            ).astype(int)
        for col, top_set in getattr(self, "top_domains_", {}).items():
            grouped_col = f"{col}_grouped"
            X[grouped_col] = np.where(
                X[col].isna(), "missing",
                np.where(X[col].isin(top_set), X[col], "other"),
            )
        return X


class FrequencyEncoder(BaseEstimator, TransformerMixin):
    """Replaces high-cardinality categorical columns with their training-fold frequency count.

    A leakage-safe alternative to target encoding for ID-like columns
    (``card1``-``card5``, ``addr1``/``addr2``, ``id_30``/``id_31``/``id_33``,
    ``DeviceInfo``): the encoding uses only the column's own value
    distribution, never the target, so it cannot leak label information.
    Categories unseen at transform time (including entirely new test-time
    values) are encoded as 0, i.e. "never observed in training" — the
    natural floor for a frequency count.
    """

    def __init__(self, columns: tuple[str, ...]) -> None:
        self.columns = columns

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> "FrequencyEncoder":
        self.frequency_maps_: dict[str, dict] = {}
        for col in self.columns:
            if col in X.columns:
                self.frequency_maps_[col] = X[col].value_counts().to_dict()
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()
        for col, freq_map in self.frequency_maps_.items():
            X[col] = X[col].map(freq_map).fillna(0).astype(float)
        return X


class CardVelocityFeatureEngineer(BaseEstimator, TransformerMixin):
    """Adds per-``card1`` transaction "velocity" aggregation features.

    Classic fraud-detection technique: how does this transaction compare to
    the historical behaviour of this card? Group statistics (count, mean,
    std of ``TransactionAmt``) are computed on the training fold only;
    ``card1`` values unseen in training fall back to the global training
    mean/count, avoiding leakage and undefined behaviour on new cards.

    EDA note: raw transaction-count-per-card1 alone showed only a weak,
    non-monotonic fraud association (2.8%-4.1% across frequency quartiles)
    in this dataset — this feature is engineered as a standard, defensible
    technique and a candidate for the pipeline, with its actual predictive
    value determined by the feature-selection stage, not assumed here.
    """

    def __init__(self, group_col: str = "card1", amount_col: str = AMOUNT_COLUMN) -> None:
        self.group_col = group_col
        self.amount_col = amount_col

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> "CardVelocityFeatureEngineer":
        if self.group_col not in X.columns or self.amount_col not in X.columns:
            self.group_stats_ = None
            return self
        grouped = X.groupby(self.group_col)[self.amount_col].agg(["count", "mean", "std"])
        grouped.columns = [f"{self.group_col}_txn_count", f"{self.group_col}_amt_mean", f"{self.group_col}_amt_std"]
        self.group_stats_ = grouped
        self.global_fallback_ = {
            f"{self.group_col}_txn_count": float(X.groupby(self.group_col).size().mean()),
            f"{self.group_col}_amt_mean": float(X[self.amount_col].mean()),
            f"{self.group_col}_amt_std": float(X[self.amount_col].std()),
        }
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()
        if getattr(self, "group_stats_", None) is None:
            return X
        merged = X.merge(self.group_stats_, how="left", left_on=self.group_col, right_index=True)
        for col, fallback_value in self.global_fallback_.items():
            merged[col] = merged[col].fillna(fallback_value)
        merged[f"{self.group_col}_amt_zscore"] = (
            (merged[self.amount_col] - merged[f"{self.group_col}_amt_mean"])
            / merged[f"{self.group_col}_amt_std"].replace(0, np.nan)
        ).fillna(0.0)
        return merged


class MissingIndicatorEngineer(BaseEstimator, TransformerMixin):
    """Adds one missing-indicator flag per *unique missingness pattern*.

    Many columns in this dataset (especially the Vesta "V" block) go missing
    in identical blocks — the same set of rows is null across dozens of
    columns simultaneously, because they come from the same upstream
    Vesta feature-generation process. Flagging every column individually
    would add ~100+ near-duplicate binary columns; instead, columns whose
    missingness exceeds ``min_missing_pct`` are grouped by an exact hash of
    their null-mask, and one indicator is emitted per group (named after
    the group's first member), collapsing redundant flags while preserving
    every distinct missingness signal.
    """

    def __init__(self, candidate_columns: tuple[str, ...], min_missing_pct: float = 5.0) -> None:
        self.candidate_columns = candidate_columns
        self.min_missing_pct = min_missing_pct

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> "MissingIndicatorEngineer":
        eligible = [
            c for c in self.candidate_columns
            if c in X.columns and X[c].isna().mean() * 100 > self.min_missing_pct
        ]
        signature_to_representative: dict[str, str] = {}
        for col in eligible:
            signature = hashlib.md5(X[col].isna().to_numpy().tobytes()).hexdigest()
            signature_to_representative.setdefault(signature, col)
        self.indicator_source_columns_: dict[str, str] = {
            f"{col}_was_missing": col for col in signature_to_representative.values()
        }
        logger.info(
            "MissingIndicatorEngineer: %d eligible columns collapsed into %d unique-pattern indicators",
            len(eligible), len(self.indicator_source_columns_),
        )
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()
        for flag_name, source_col in getattr(self, "indicator_source_columns_", {}).items():
            X[flag_name] = X[source_col].isna().astype(int)
        return X
