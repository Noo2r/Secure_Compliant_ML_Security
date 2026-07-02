from datetime import datetime, timezone

import pandas as pd
import pytest

from src.config.config_loader import AppConfig
from src.data.classification_registry import DataClassificationRegistry
from src.data.secure_data_loader import DatasetManifest
from src.data.validators import DataValidator

_FAKE_TOKEN = "gAAAAABfakeTokenForTestingOnly=="


def _make_manifest(lineage_ok: bool = True) -> DatasetManifest:
    return DatasetManifest(
        mode="regenerate",
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        row_count=3,
        column_count=10,
        dropped_column_count=12,
        dropped_columns=tuple(),
        pii_columns=("CustomerName", "Email", "PhoneNumber", "Address", "NationalID"),
        sensitive_columns=("addr1",),
        encrypted_columns=("CustomerName", "Email", "PhoneNumber", "Address", "NationalID", "CreditCardNumber"),
        target_column="isFraud",
        source_file_hashes={},
        dataset_version="deadbeef",
        lineage_check_passed=lineage_ok,
    )


def _valid_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "TransactionID": [1, 2, 3],
            "isFraud": [0, 1, 0],
            "TransactionDT": [100, 200, 300],
            "TransactionAmt": [10.5, 20.0, 5.25],
            "CustomerName": [_FAKE_TOKEN, _FAKE_TOKEN, None],
            "Email": [_FAKE_TOKEN, _FAKE_TOKEN, _FAKE_TOKEN],
            "PhoneNumber": [_FAKE_TOKEN, _FAKE_TOKEN, _FAKE_TOKEN],
            "Address": [_FAKE_TOKEN, _FAKE_TOKEN, _FAKE_TOKEN],
            "NationalID": [_FAKE_TOKEN, _FAKE_TOKEN, _FAKE_TOKEN],
            "CreditCardNumber": [_FAKE_TOKEN, _FAKE_TOKEN, _FAKE_TOKEN],
            "addr1": [100.0, 200.0, 300.0],
        }
    )


def test_valid_dataframe_passes_all_critical_checks(
    app_config: AppConfig, classification_registry: DataClassificationRegistry
) -> None:
    validator = DataValidator(app_config, classification_registry)
    report = validator.validate(_valid_dataframe(), _make_manifest())
    assert report.passed is True


def test_duplicate_transaction_id_fails_merge_integrity(
    app_config: AppConfig, classification_registry: DataClassificationRegistry
) -> None:
    df = _valid_dataframe()
    df.loc[2, "TransactionID"] = 1  # duplicate key
    validator = DataValidator(app_config, classification_registry)
    report = validator.validate(df, _make_manifest())
    assert report.passed is False
    failed_names = {c.name for c in report.checks if not c.passed and c.severity == "critical"}
    assert "merge_key_unique" in failed_names


def test_non_binary_target_fails_validation(
    app_config: AppConfig, classification_registry: DataClassificationRegistry
) -> None:
    df = _valid_dataframe()
    df.loc[0, "isFraud"] = 2
    validator = DataValidator(app_config, classification_registry)
    report = validator.validate(df, _make_manifest())
    assert report.passed is False


def test_plaintext_pii_value_fails_encryption_check(
    app_config: AppConfig, classification_registry: DataClassificationRegistry
) -> None:
    df = _valid_dataframe()
    df.loc[0, "Email"] = "not-encrypted@example.com"
    validator = DataValidator(app_config, classification_registry)
    report = validator.validate(df, _make_manifest())
    assert report.passed is False
    failed_names = {c.name for c in report.checks if not c.passed and c.severity == "critical"}
    assert "pii_columns_encrypted" in failed_names


def test_lineage_mismatch_is_warning_not_failure(
    app_config: AppConfig, classification_registry: DataClassificationRegistry
) -> None:
    validator = DataValidator(app_config, classification_registry)
    report = validator.validate(_valid_dataframe(), _make_manifest(lineage_ok=False))
    lineage_check = next(c for c in report.checks if c.name == "lineage_consistency")
    assert lineage_check.severity == "warning"
    assert lineage_check.passed is False
    # A warning-severity failure must not flip the overall report to failed.
    assert report.passed is True
