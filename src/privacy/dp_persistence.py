"""Persistence for trained Normal/DP models: weights, architecture config,
training metadata, and privacy metadata, saved as one self-describing unit
per model variant.

Uses Keras's own native ``.save()``/``load_model()`` format for weights
(the correct, library-blessed serialization for a Keras model, rather than
joblib/pickle) alongside a plain JSON metadata sidecar -- readable without
even loading TensorFlow, useful for quick audits of what was trained.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.privacy import tf_privacy_compat  # noqa: F401 -- must precede tensorflow import
from src.privacy.privacy_accountant import PrivacyBudget
from src.utils.logger import get_logger

logger = get_logger(__name__)

_MODEL_FILENAME = "model.keras"
_METADATA_FILENAME = "metadata.json"


@dataclass(frozen=True)
class DPModelMetadata:
    """Everything needed to know what a saved model is, without loading it."""

    variant: str  # "normal" | "dp"
    dataset_version: str
    architecture_params: dict
    batch_size: int
    epochs: int
    train_seconds: float
    random_state: int
    saved_at_utc: str
    privacy_params: Optional[dict] = None  # {l2_norm_clip, noise_multiplier, microbatches}, None for "normal"
    privacy_budget: Optional[dict] = None  # PrivacyBudget.to_dict(), None for "normal"

    def to_dict(self) -> dict:
        return asdict(self)


class DPModelArtifact:
    """Saves/loads one trained model variant (weights + full metadata)."""

    @staticmethod
    def save(
        model: Any,
        variant: str,
        dataset_version: str,
        architecture_params: dict,
        batch_size: int,
        epochs: int,
        train_seconds: float,
        random_state: int,
        output_dir: Path,
        privacy_params: Optional[dict] = None,
        privacy_budget: Optional[PrivacyBudget] = None,
    ) -> DPModelMetadata:
        output_dir.mkdir(parents=True, exist_ok=True)

        # TF-Privacy's DP optimizer (DPOptimizerClass) is not registered with
        # Keras's serializable-object registry, so saving a model still
        # compiled with it produces a file that raises
        # `TypeError: Could not locate class 'DPOptimizerClass'` on load --
        # verified directly (not assumed) via this module's own persistence
        # test. The optimizer's internal state is meaningless after training
        # ends anyway (DP-SGD is not meant to be resumed -- resuming would
        # invalidate the already-computed privacy budget), so the model is
        # recompiled with a plain, natively-serializable optimizer
        # immediately before saving. This only replaces the optimizer slot;
        # it does not alter the already-trained weights being persisted.
        from tensorflow import keras
        model.compile(optimizer=keras.optimizers.Adam(), loss="binary_crossentropy")
        model.save(output_dir / _MODEL_FILENAME)

        metadata = DPModelMetadata(
            variant=variant,
            dataset_version=dataset_version,
            architecture_params=architecture_params,
            batch_size=batch_size,
            epochs=epochs,
            train_seconds=train_seconds,
            random_state=random_state,
            saved_at_utc=datetime.now(timezone.utc).isoformat(),
            privacy_params=privacy_params,
            privacy_budget=privacy_budget.to_dict() if privacy_budget is not None else None,
        )
        with open(output_dir / _METADATA_FILENAME, "w", encoding="utf-8") as fh:
            json.dump(metadata.to_dict(), fh, indent=2)

        logger.info("Saved %s model (weights + metadata) to %s", variant, output_dir)
        return metadata

    @staticmethod
    def load(model_dir: Path) -> tuple[Any, DPModelMetadata]:
        from tensorflow import keras

        with open(model_dir / _METADATA_FILENAME, "r", encoding="utf-8") as fh:
            metadata_dict = json.load(fh)
        model = keras.models.load_model(model_dir / _MODEL_FILENAME)
        return model, DPModelMetadata(**metadata_dict)
