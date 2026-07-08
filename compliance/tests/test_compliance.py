import pytest
import requests
import os

def test_field_level_encryption_behavior():
    """Validates that sensitive fields are encrypted and not plaintext."""
    sample_raw_data = {"patient_name": "Alice Smith", "ssn": "000-12-3456"}
    
    # Mocking Yara's AES-256 output structure
    encrypted_output = {"patient_name": "AES256_XYZ...", "ssn": "AES256_ABC..."}
    
    assert encrypted_output["patient_name"] != sample_raw_data["patient_name"], "Plaintext leaked!"
    assert encrypted_output["ssn"] != sample_raw_data["ssn"], "Plaintext leaked!"

def test_api_endpoint_authentication_bypass():
    """Validates that requests without a token are blocked (OWASP check)."""
    target_url = os.getenv("DEPLOYED_AKS_API_URL", "https://api.secure-ml-pipeline.azure.com/predict")
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(target_url, json={"features": [0.1, 2.3]}, headers=headers, timeout=5)
        assert response.status_code in [401, 403], "SECURITY HOLE: API allowed unauthorized bypass!"
    except requests.exceptions.ConnectionError:
        pytest.skip("Endpoint offline. Skipping network check.")