"""Decision-threshold optimization.

The default 0.5 classification threshold is inappropriate under a 3.5%
positive rate -- it is calibrated for a balanced problem this dataset is
not. This module picks a threshold on a validation slice carved out of the
TRAINING data (never the final test set), so the threshold choice itself
cannot leak information from the holdout used for final model comparison.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from sklearn.metrics import f1_score, precision_recall_curve

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ThresholdDecision:
    strategy: str
    threshold: float
    precision_at_threshold: float
    recall_at_threshold: float
    f1_at_threshold: float

    def to_dict(self) -> dict[str, float | str]:
        return asdict(self)


def optimize_threshold(
    y_val: np.ndarray, y_proba_val: np.ndarray, strategy: str = "max_f1", min_precision: float = 0.5
) -> ThresholdDecision:
    """Selects a decision threshold from validation predictions.

    Parameters
    ----------
    strategy:
        ``"max_f1"`` -- threshold maximizing F1 on the validation slice.
        ``"recall_at_precision"`` -- highest-recall threshold with precision
        at or above ``min_precision`` (a fixed-review-capacity framing).
    """
    precision, recall, thresholds = precision_recall_curve(y_val, y_proba_val)
    precision, recall = precision[:-1], recall[:-1]  # align with thresholds

    if strategy == "max_f1":
        f1_scores = np.where(
            (precision + recall) > 0, 2 * precision * recall / (precision + recall + 1e-12), 0.0
        )
        best_idx = int(np.argmax(f1_scores))
    elif strategy == "recall_at_precision":
        meets_floor = precision >= min_precision
        if meets_floor.any():
            candidate_recalls = np.where(meets_floor, recall, -np.inf)
            best_idx = int(np.argmax(candidate_recalls))
        else:
            best_idx = int(np.argmax(precision))
            logger.warning(
                "No threshold reached min_precision=%.3f; falling back to the highest-precision "
                "threshold available (%.3f).", min_precision, precision[best_idx],
            )
    else:
        raise ValueError(f"Unknown threshold strategy '{strategy}'")

    chosen_threshold = float(thresholds[best_idx])
    y_pred_at_threshold = (y_proba_val >= chosen_threshold).astype(int)
    decision = ThresholdDecision(
        strategy=strategy,
        threshold=chosen_threshold,
        precision_at_threshold=float(precision[best_idx]),
        recall_at_threshold=float(recall[best_idx]),
        f1_at_threshold=float(f1_score(y_val, y_pred_at_threshold, zero_division=0)),
    )
    logger.info("Threshold optimization (%s): %s", strategy, decision)
    return decision
