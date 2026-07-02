import pandas as pd

from src.data.classification_registry import DataClassificationRegistry
from src.features.dataset_utils import build_ml_ready_frame, extract_metadata_frame


def test_build_ml_ready_frame_drops_only_encrypted_columns(
    classification_registry: DataClassificationRegistry,
) -> None:
    df = pd.DataFrame({
        "TransactionID": [1, 2],
        "isFraud": [0, 1],
        "TransactionAmt": [10.0, 20.0],
        "CustomerName": ["gAAAAAtoken1", "gAAAAAtoken2"],
        "CreditCardNumber": ["gAAAAAcc1", "gAAAAAcc2"],
        "addr1": [100.0, 200.0],
    })
    out = build_ml_ready_frame(df, classification_registry)
    assert "CustomerName" not in out.columns
    assert "CreditCardNumber" not in out.columns
    assert "TransactionAmt" in out.columns
    assert "addr1" in out.columns


def test_extract_metadata_frame_preserves_index_and_values() -> None:
    df = pd.DataFrame(
        {"TransactionID": [10, 20, 30], "card6": ["debit", "credit", "debit"], "V1": [1.0, 2.0, 3.0]},
        index=[100, 101, 102],
    )
    metadata = extract_metadata_frame(df, ["TransactionID", "card6"])
    assert list(metadata.columns) == ["TransactionID", "card6"]
    assert list(metadata.index) == [100, 101, 102]
    assert "V1" not in metadata.columns


def test_extract_metadata_frame_skips_missing_columns_with_warning() -> None:
    df = pd.DataFrame({"TransactionID": [1, 2]})
    metadata = extract_metadata_frame(df, ["TransactionID", "does_not_exist"])
    assert list(metadata.columns) == ["TransactionID"]
