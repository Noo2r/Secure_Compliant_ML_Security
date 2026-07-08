import logging
import uuid

from fastapi import APIRouter, Depends, Request

from app.core.config import get_settings
from app.core.limiter import limiter
from app.core.security import TokenData, require_role
from app.models.model_loader import get_model_service
from app.models.raw_schema import CORE_FIELD_NAMES, build_ml_ready_frame
from app.models.schemas import PredictionResponse, TransactionFeatures

router = APIRouter(prefix="/inference", tags=["inference"])

logger = logging.getLogger("fraud_api.inference")


def _to_ml_ready_frame(features: TransactionFeatures):
    """Builds the single-row raw ML-ready DataFrame InferenceBundle.predict_proba()
    expects — see app/models/raw_schema.py for why this is a DataFrame (not a
    bare ndarray) and why unset columns default to NaN rather than being omitted.
    """
    core_values = {name: getattr(features, name) for name in CORE_FIELD_NAMES}
    return build_ml_ready_frame(core_values, features.extra_features)


@router.post("/predict", response_model=PredictionResponse)
@limiter.limit(get_settings().RATE_LIMIT)
def predict(
    request: Request,
    features: TransactionFeatures,
    current_user: TokenData = Depends(require_role("ml_engineer", "service_client")),
):
    request_id = str(uuid.uuid4())

    # Audit log: WHO called WHAT, never log raw feature values (may be
    # derived from PII) or the prediction payload itself.
    logger.info(
        "inference_request request_id=%s user=%s role=%s",
        request_id, current_user.subject, current_user.role,
    )

    model_service = get_model_service()
    ml_ready_frame = _to_ml_ready_frame(features)
    is_fraud, probability = model_service.predict(ml_ready_frame)

    return PredictionResponse(
        is_fraud=is_fraud,
        fraud_probability=round(probability, 4),
        model_version=model_service.version,
        request_id=request_id,
    )
