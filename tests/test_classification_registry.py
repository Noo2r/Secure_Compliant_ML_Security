from src.data.classification_registry import DataClassificationRegistry

# data_classification.csv labels these 5 as "PII" (CreditCardNumber is
# labeled "Financial" there, alongside the unencrypted TransactionAmt).
_EXPECTED_PII_LABEL = {"CustomerName", "Email", "PhoneNumber", "Address", "NationalID"}

# data_lineage.csv's "PII Columns" step lists the true set of 6 Fernet-encrypted
# columns (the ground truth for what must never be used as a raw feature).
_EXPECTED_ENCRYPTED = _EXPECTED_PII_LABEL | {"CreditCardNumber"}


def test_pii_columns_match_yaras_classification_report(
    classification_registry: DataClassificationRegistry,
) -> None:
    assert set(classification_registry.pii_columns) == _EXPECTED_PII_LABEL


def test_encrypted_columns_include_creditcardnumber_despite_financial_label(
    classification_registry: DataClassificationRegistry,
) -> None:
    # CreditCardNumber is classified "Financial" in data_classification.csv
    # but IS encrypted per data_lineage.csv -- encrypted_columns must reflect
    # the lineage ground truth, not the classification label.
    assert set(classification_registry.encrypted_columns) == _EXPECTED_ENCRYPTED
    assert "CreditCardNumber" in classification_registry.encrypted_columns


def test_target_column_is_isfraud(classification_registry: DataClassificationRegistry) -> None:
    assert classification_registry.target_column == "isFraud"


def test_sensitive_columns_are_not_encrypted(classification_registry: DataClassificationRegistry) -> None:
    assert set(classification_registry.sensitive_columns).isdisjoint(set(classification_registry.encrypted_columns))


def test_feature_blocklist_is_encrypted_columns_not_just_pii_label(
    classification_registry: DataClassificationRegistry,
) -> None:
    assert classification_registry.feature_blocklist() == set(classification_registry.encrypted_columns)
    assert "CreditCardNumber" in classification_registry.feature_blocklist()
    # TransactionAmt shares the "Financial" label with CreditCardNumber but is
    # NOT encrypted, so it must remain usable as a model feature.
    assert "TransactionAmt" not in classification_registry.feature_blocklist()


def test_expected_columns_dropped_matches_lineage_report(
    classification_registry: DataClassificationRegistry,
) -> None:
    assert classification_registry.expected_columns_dropped == 12


def test_validate_column_drop_count_flags_mismatch(
    classification_registry: DataClassificationRegistry,
) -> None:
    assert classification_registry.validate_column_drop_count(12) is True
    assert classification_registry.validate_column_drop_count(5) is False
