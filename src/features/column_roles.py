"""Domain-driven column-role constants for the IEEE-CIS fraud dataset.

These lists are NOT guessed from dtypes alone — they were derived from the
Module 2 EDA pass (see ``reports_m2/eda_profile_report.md``) that inspected
actual cardinality, missingness, and dtype of every surviving column in the
Module 1 ML-ready frame. Centralizing them here (rather than re-deriving
column roles inside every transformer) is the single source of truth every
Module 2 component imports from, avoiding drift and duplicate logic.

Card/address identifiers (``card1``-``card5``, ``addr1``, ``addr2``) are
stored as numeric dtype in the raw data but are semantically categorical IDs
(a card network/issuer/region code, not a continuous quantity where
magnitude is meaningful) — confirmed by cardinality (e.g. ``card1`` has
13,553 unique values, ``card3`` only 114). They are treated as high-cardinality
categoricals here, not scaled as ordinary numeric features.
"""

from __future__ import annotations

TARGET_COLUMN = "isFraud"
TIME_COLUMN = "TransactionDT"
AMOUNT_COLUMN = "TransactionAmt"
MERGE_KEY_COLUMN = "TransactionID"

# Numeric-dtype columns that are semantically ID-like categoricals, not
# continuous quantities. Frequency-encoded rather than scaled.
ID_LIKE_HIGH_CARDINALITY_NUMERIC = ("card1", "card2", "card3", "card5", "addr1", "addr2")

# Low-cardinality object-dtype columns (<=5 categories): safe for one-hot encoding.
LOW_CARDINALITY_CATEGORICAL = (
    "ProductCD", "card4", "card6",
    "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9",
    "id_12", "id_15", "id_16", "id_28", "id_29", "id_34",
    "id_35", "id_36", "id_37", "id_38", "DeviceType",
)

# High-cardinality object-dtype columns: one-hot would explode dimensionality,
# so these are frequency-encoded (id_30/id_31/id_33/DeviceInfo) or grouped
# into a small set of top categories + "other" (email domains, which carry a
# strong, uneven fraud signal per category -- see EDA report).
HIGH_CARDINALITY_CATEGORICAL_GROUPED = ("P_emaildomain", "R_emaildomain")
HIGH_CARDINALITY_CATEGORICAL_FREQUENCY = ("id_30", "id_31", "id_33", "DeviceInfo")

# Columns with material missingness (>5%) where the fact that a value is
# missing is itself informative (e.g. DeviceType missing correlates with a
# ~4x lower fraud rate than DeviceType present -- see EDA report) and
# therefore gets its own missing-indicator feature, in addition to imputation.
MISSING_INDICATOR_CANDIDATE_PREFIXES = ("D", "id_", "V")
MISSING_INDICATOR_EXPLICIT_COLUMNS = ("DeviceType", "DeviceInfo", "P_emaildomain", "R_emaildomain")

# Vesta engineered feature block: highly redundant, correlation-filtered in
# the feature-selection stage rather than hand-picked.
V_COLUMN_PREFIX = "V"
C_COLUMN_PREFIX = "C"
D_COLUMN_PREFIX = "D"

EMAIL_DOMAIN_TOP_N = 15  # top-N most frequent domains kept distinct; remainder -> "other"
