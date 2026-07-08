"""
The real raw feature contract for Nour El-Din's Module 2/3 pipeline.

`InferenceBundle.predict_proba()` (src/models/inference_bundle.py) expects a
raw, pre-engineering "ML-ready" DataFrame -- the same shape of data
Milestone 2's `engineering_pipeline` was fit on (Module 1's secured dataset
minus the 6 Fernet-encrypted PII columns). This list is the literal column
header of that dataset (data/encrypted/encrypted_dataset.csv, 428 columns),
verified directly against the committed artifact rather than assumed from
IEEE-CIS documentation -- see reports_m2/dataset_manifest.json
(column_count: 428) and reports_m2/feature_manifest.json for the
cross-check.

Hand-enumerating all ~420 columns as individually-typed Pydantic fields is
not a reasonable REST API surface, so this module splits them into:

  * CORE_FIELDS -- the raw columns the engineering transformers in
    src/features/engineering.py actually read to derive features
    (TimeFeatureEngineer needs TransactionDT; TransactionAmountFeatureEngineer
    needs TransactionAmt; EmailDomainGrouper needs P_emaildomain/
    R_emaildomain; CardVelocityFeatureEngineer needs card1; FrequencyEncoder
    is fit on exactly id_30/id_31/id_33/DeviceInfo per
    scripts/run_module2.py) plus the highest-value raw pass-through
    predictors from reports_m2/feature_manifest.json's selected_features
    list (ProductCD, card2/3/5/6, addr1). These get individual, validated
    Pydantic fields.
  * EXTRA_ALLOWED_COLUMNS -- every other raw column (the C*/D*/M*/V*/id_*
    long tail). MissingIndicatorEngineer's candidate set alone covers most
    D*/V*/id_* columns (see scripts/run_module2.py), so these are real,
    used inputs, not incidental ones -- exposed as an open `extra_features`
    dict rather than ~400 individual fields.

Every column not supplied by a request defaults to NaN in the assembled
DataFrame, which is exactly how src/features/engineering.py's transformers
are designed to handle missing/unseen values (frequency-encoded as 0,
grouped to "missing", detected by MissingIndicatorEngineer) -- so a
partially-filled request is not a special case, it's the normal path.
"""
import numpy as np
import pandas as pd

# Full 428-column header of data/encrypted/encrypted_dataset.csv, verified
# directly (not assumed) via the committed dataset.
_ALL_RAW_COLUMNS: tuple[str, ...] = (
    "TransactionID", "isFraud", "TransactionDT", "TransactionAmt", "ProductCD",
    "card1", "card2", "card3", "card4", "card5", "card6",
    "addr1", "addr2", "dist1", "P_emaildomain", "R_emaildomain",
    "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C11", "C12", "C13", "C14",
    "D1", "D2", "D3", "D4", "D5", "D6", "D8", "D9", "D10", "D11", "D12", "D13", "D14", "D15",
    "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9",
    *[f"V{i}" for i in range(1, 340)],
    "id_01", "id_02", "id_03", "id_04", "id_05", "id_06", "id_09", "id_10", "id_11",
    "id_12", "id_13", "id_14", "id_15", "id_16", "id_17", "id_19", "id_20",
    "id_28", "id_29", "id_30", "id_31", "id_32", "id_33", "id_34", "id_35", "id_36", "id_37", "id_38",
    "DeviceType", "DeviceInfo",
    "CustomerName", "Email", "PhoneNumber", "Address", "NationalID", "CreditCardNumber",
)

# The 6 Fernet-encrypted columns (src/data/classification_registry.py's
# feature_blocklist()) plus the target -- never part of a feature request.
_EXCLUDED_COLUMNS = frozenset({
    "isFraud",
    "CustomerName", "Email", "PhoneNumber", "Address", "NationalID", "CreditCardNumber",
})

# The raw ML-ready feature contract: everything the engineering_pipeline was
# actually fit on. 421 columns (428 - 6 encrypted - 1 target).
RAW_ML_READY_COLUMNS: tuple[str, ...] = tuple(
    c for c in _ALL_RAW_COLUMNS if c not in _EXCLUDED_COLUMNS
)

# Explicit, individually-validated request fields.
CORE_FIELD_NAMES: frozenset[str] = frozenset({
    "TransactionID", "TransactionDT", "TransactionAmt", "ProductCD",
    "card1", "card2", "card3", "card4", "card5", "card6", "addr1",
    "P_emaildomain", "R_emaildomain", "DeviceType", "DeviceInfo",
    "id_30", "id_31", "id_33",
})

# Everything else the request may optionally supply via `extra_features`.
EXTRA_ALLOWED_COLUMNS: frozenset[str] = frozenset(RAW_ML_READY_COLUMNS) - CORE_FIELD_NAMES


def build_ml_ready_frame(core_values: dict, extra_features: dict) -> pd.DataFrame:
    """Assembles a single-row raw ML-ready DataFrame for InferenceBundle.predict_proba().

    Starts from an all-NaN template covering the FULL raw column contract
    (matching what engineering_pipeline.fit() saw), then overlays whatever
    the request actually supplied. Every column the pipeline might read is
    always present -- callers only need to supply the subset they have.
    """
    row = {col: np.nan for col in RAW_ML_READY_COLUMNS}
    row.update({k: v for k, v in core_values.items() if v is not None})
    row.update(extra_features)
    return pd.DataFrame([row], columns=RAW_ML_READY_COLUMNS)
