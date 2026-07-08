"""
Request/response schemas for the inference endpoint.

Strict typing + bounds act as the first line of defence (input validation)
against malformed input, injection attempts, and resource-exhaustion payloads —
mapping to the OWASP API Security Top 10 (API3: Broken Object Property Level
Authorization / API8: Security Misconfiguration mitigations start here).

TransactionFeatures models the REAL raw feature contract of Nour El-Din's
trained model (see app/models/raw_schema.py for how this was derived from
the actual committed Module 2 artifacts) — not a placeholder subset.
"""
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.raw_schema import EXTRA_ALLOWED_COLUMNS


class TransactionFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")  # reject unexpected/extra fields

    # --- Identity / metadata (not model input, carried through for tracing) ---
    TransactionID: Optional[int] = Field(default=None, ge=0)

    # --- Core fields the engineering pipeline reads directly ---
    # (src/features/engineering.py: TimeFeatureEngineer, TransactionAmountFeatureEngineer,
    # EmailDomainGrouper, CardVelocityFeatureEngineer, FrequencyEncoder)
    TransactionDT: Optional[int] = Field(default=None, ge=0, description="Seconds since dataset reference point")
    TransactionAmt: float = Field(..., ge=0, le=1_000_000, description="Transaction amount")
    ProductCD: str = Field(..., max_length=10)
    card1: Optional[int] = Field(default=None, ge=0)
    card2: Optional[float] = Field(default=None, ge=0)
    card3: Optional[float] = Field(default=None, ge=0)
    card4: Optional[str] = Field(default=None, max_length=20, description="Card network, e.g. visa/mastercard")
    card5: Optional[float] = Field(default=None, ge=0)
    card6: Optional[str] = Field(default=None, max_length=20, description="debit/credit")
    addr1: Optional[float] = Field(default=None, ge=0)
    P_emaildomain: Optional[str] = Field(default=None, max_length=100)
    R_emaildomain: Optional[str] = Field(default=None, max_length=100)
    DeviceType: Optional[str] = Field(default=None, max_length=20)
    DeviceInfo: Optional[str] = Field(default=None, max_length=200)
    id_30: Optional[str] = Field(default=None, max_length=100, description="OS")
    id_31: Optional[str] = Field(default=None, max_length=100, description="Browser")
    id_33: Optional[str] = Field(default=None, max_length=50, description="Screen resolution")

    # --- Long tail: C1-C14, D1-D15, M1-M9, V1-V339, remaining id_* columns ---
    # Open passthrough (bounded, key-validated) instead of ~400 individual
    # fields — see app/models/raw_schema.py for the exact rationale and the
    # full list of columns this pipeline was actually fit on.
    extra_features: dict[str, Union[float, str, None]] = Field(default_factory=dict)

    @field_validator("extra_features")
    @classmethod
    def _validate_extra_feature_keys(cls, value: dict) -> dict:
        if len(value) > 200:
            raise ValueError("extra_features has too many entries")
        unknown = set(value) - EXTRA_ALLOWED_COLUMNS
        if unknown:
            raise ValueError(
                f"extra_features contains columns this model was not trained on: {sorted(unknown)[:10]}"
            )
        return value


class PredictionResponse(BaseModel):
    is_fraud: bool
    fraud_probability: float
    model_version: str
    request_id: str
