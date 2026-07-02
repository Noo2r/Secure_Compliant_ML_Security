"""Unit tests for SecureDatasetLoader.regenerate(), using tiny synthetic raw
CSVs instead of the real 590k-row / 683MB IEEE-CIS files, so this test suite
stays fast enough to run on every commit.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pandas as pd
import pytest

from src.config.config_loader import AppConfig
from src.data.classification_registry import DataClassificationRegistry
from src.data.secure_data_loader import SecureDatasetLoader

_FERNET_PREFIX = "gAAAAA"


@pytest.fixture()
def tiny_raw_config(app_config: AppConfig, tmp_path: Path) -> AppConfig:
    transaction_df = pd.DataFrame(
        {
            "TransactionID": [1, 2, 3, 4, 5],
            "isFraud": [0, 1, 0, 0, 1],
            "TransactionDT": [100, 200, 300, 400, 500],
            "TransactionAmt": [10.0, 20.0, 30.0, 40.0, 50.0],
            # 100% missing -> must be dropped by regeneration logic (threshold is 90%)
            "MostlyMissing": [None, None, None, None, None],
        }
    )
    identity_df = pd.DataFrame({"TransactionID": [1, 2, 3], "id_01": [0.1, 0.2, 0.3]})

    tx_path = tmp_path / "train_transaction.csv"
    id_path = tmp_path / "train_identity.csv"
    transaction_df.to_csv(tx_path, index=False)
    identity_df.to_csv(id_path, index=False)

    new_paths = dataclasses.replace(
        app_config.paths,
        raw_transaction_csv=tx_path,
        raw_identity_csv=id_path,
        encrypted_dataset_csv=tmp_path / "encrypted_dataset.csv",
        encryption_key_file=tmp_path / "secret.key",
    )
    new_secure_data = dataclasses.replace(app_config.secure_data, mode="regenerate")
    return dataclasses.replace(app_config, paths=new_paths, secure_data=new_secure_data)


def test_regenerate_drops_high_missing_columns(
    tiny_raw_config: AppConfig, classification_registry: DataClassificationRegistry
) -> None:
    loader = SecureDatasetLoader(tiny_raw_config, classification_registry)
    df, manifest = loader.load()
    assert "MostlyMissing" not in df.columns
    assert manifest.dropped_column_count == 1
    assert "MostlyMissing" in manifest.dropped_columns


def test_regenerate_injects_and_encrypts_all_lineage_columns(
    tiny_raw_config: AppConfig, classification_registry: DataClassificationRegistry
) -> None:
    """Every column in the lineage-report's encrypted set must be ciphertext,
    including CreditCardNumber -- which is mislabeled "Financial" (not "PII")
    in data_classification.csv and would be silently left in plaintext if the
    loader encrypted only registry.pii_columns instead of registry.encrypted_columns.
    """
    loader = SecureDatasetLoader(tiny_raw_config, classification_registry)
    df, _ = loader.load()
    assert "CreditCardNumber" in classification_registry.encrypted_columns
    for col in classification_registry.encrypted_columns:
        assert col in df.columns
        non_null = df[col].dropna()
        assert non_null.str.startswith(_FERNET_PREFIX).all()


def test_regenerate_preserves_row_count_with_left_join(
    tiny_raw_config: AppConfig, classification_registry: DataClassificationRegistry
) -> None:
    loader = SecureDatasetLoader(tiny_raw_config, classification_registry)
    df, manifest = loader.load()
    assert len(df) == 5  # left join on transaction rows must not drop or fan out rows
    assert manifest.row_count == 5


def test_encryption_key_file_is_written_and_not_a_feature(
    tiny_raw_config: AppConfig, classification_registry: DataClassificationRegistry
) -> None:
    loader = SecureDatasetLoader(tiny_raw_config, classification_registry)
    df, _ = loader.load()
    assert tiny_raw_config.paths.encryption_key_file.exists()
    assert "key" not in {c.lower() for c in df.columns}


def test_dataset_version_is_deterministic_for_same_structure(
    tiny_raw_config: AppConfig, classification_registry: DataClassificationRegistry
) -> None:
    loader = SecureDatasetLoader(tiny_raw_config, classification_registry)
    df, manifest = loader.load()
    # Recomputing the version from the same structural fingerprint (columns,
    # row count, dropped columns, target distribution) must be stable even
    # though the encrypted PII values themselves differ between runs.
    version_again = SecureDatasetLoader._compute_dataset_version(df, list(manifest.dropped_columns))
    assert version_again == manifest.dataset_version
