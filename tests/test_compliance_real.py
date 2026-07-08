"""Real compliance validation for Milestone 4 (Farida Elgharbawy).

Farida's original compliance suite (compliance/tests/test_compliance.py,
kept verbatim/unmodified for attribution) was intended to validate two
things but doesn't actually exercise either:

  * test_field_level_encryption_behavior hardcodes a fake "encrypted_output"
    dict inline and compares it to an equally fake plaintext dict it made up
    -- it never touches Module 1's real encryption-verification code.
  * test_api_endpoint_authentication_bypass POSTs to a hardcoded placeholder
    URL that was never deployed (no live Azure subscription exists -- see
    the Milestone 3 integration notes), so it always hits ConnectionError
    and pytest.skip()s -- it never actually asserts anything.

This file implements what those two tests were meant to validate, against
this project's real, running code, so the compliance claim is backed by an
executable, always-runnable check rather than a mock and a network skip.
"""
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from src.data.validators import DataValidator, _FERNET_TOKEN_PREFIX


def test_real_fernet_ciphertext_passes_pii_encryption_check(app_config, classification_registry) -> None:
    """Genuine Fernet ciphertext (not a hand-typed fake token) must be
    recognized as encrypted by the same check Module 1 runs in production.

    This is the real version of Farida's encryption test: instead of
    asserting a made-up "encrypted" string differs from a made-up plaintext
    string (true by construction, proves nothing), this generates real
    ciphertext with the same library Module 1 uses and confirms the actual
    validator recognizes it.
    """
    key = Fernet.generate_key()
    fernet = Fernet(key)
    real_ciphertext = fernet.encrypt(b"Alice Smith").decode("utf-8")
    plaintext = "Alice Smith"

    assert real_ciphertext != plaintext, "Fernet ciphertext must not equal the plaintext it encrypts"
    assert real_ciphertext.startswith(_FERNET_TOKEN_PREFIX), (
        "Real Fernet output must start with the version-byte prefix Module 1's "
        "validator checks for"
    )
    assert not plaintext.startswith(_FERNET_TOKEN_PREFIX)

    df = _minimal_ml_ready_dataframe(pii_value=real_ciphertext)
    validator = DataValidator(app_config, classification_registry)
    report = validator.validate(df, _minimal_manifest())

    encryption_check = next(c for c in report.checks if c.name == "pii_columns_encrypted")
    assert encryption_check.passed is True


def test_real_plaintext_pii_fails_the_same_check(app_config, classification_registry) -> None:
    """The mirror case: real plaintext must be caught, not waved through."""
    df = _minimal_ml_ready_dataframe(pii_value="Alice Smith")  # plaintext, not encrypted
    validator = DataValidator(app_config, classification_registry)
    report = validator.validate(df, _minimal_manifest())

    encryption_check = next(c for c in report.checks if c.name == "pii_columns_encrypted")
    assert encryption_check.passed is False
    assert report.passed is False


def test_inference_api_rejects_unauthenticated_requests() -> None:
    """The real version of Farida's API-bypass test: instead of POSTing to a
    hardcoded, never-deployed Azure URL and silently skipping on
    ConnectionError, this runs the actual FastAPI app in-process (no network
    dependency) and asserts the real 401 behavior -- the same check
    performed manually via curl during the Milestone 3 integration, now a
    permanent regression test.
    """
    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/api/v1/inference/predict",
        json={"TransactionAmt": 100.0, "ProductCD": "W"},
    )
    assert response.status_code == 401, "SECURITY HOLE: API allowed an unauthenticated request through"


def _minimal_manifest():
    from datetime import datetime, timezone

    from src.data.secure_data_loader import DatasetManifest

    return DatasetManifest(
        mode="regenerate",
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        row_count=1,
        column_count=10,
        dropped_column_count=12,
        dropped_columns=tuple(),
        pii_columns=("CustomerName", "Email", "PhoneNumber", "Address", "NationalID"),
        sensitive_columns=("addr1",),
        encrypted_columns=("CustomerName", "Email", "PhoneNumber", "Address", "NationalID", "CreditCardNumber"),
        target_column="isFraud",
        source_file_hashes={},
        dataset_version="deadbeef",
        lineage_check_passed=True,
    )


def _minimal_ml_ready_dataframe(pii_value: str):
    import pandas as pd

    return pd.DataFrame({
        "TransactionID": [1],
        "isFraud": [0],
        "TransactionDT": [100],
        "TransactionAmt": [10.5],
        "CustomerName": [pii_value],
        "Email": [pii_value],
        "PhoneNumber": [pii_value],
        "Address": [pii_value],
        "NationalID": [pii_value],
        "CreditCardNumber": [pii_value],
        "addr1": [100.0],
    })
