"""Diagnostic tooling for root-causing DP-SGD utility loss.

Unlike the rest of ``src.privacy``, this module is not part of the
production training pipeline -- it exists to answer a specific empirical
question with measurements, not assumptions: *how large are per-example
gradients on this architecture/data, relative to the configured
``l2_norm_clip``?* If typical gradient norms are far above the clip bound,
clipping is discarding most of the gradient's magnitude information on
(almost) every step, which is a directly falsifiable, measurable claim --
not a theoretical guess.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.privacy import tf_privacy_compat  # noqa: F401 -- must precede tensorflow import
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class GradientNormReport:
    """Per-example gradient L2 norm statistics for one class of examples."""

    label: str  # "positive" | "negative" | "all"
    n_examples: int
    mean: float
    median: float
    p10: float
    p90: float
    min: float
    max: float
    fraction_above_clip: float  # fraction of examples whose raw gradient norm exceeds l2_norm_clip
    l2_norm_clip: float

    def to_dict(self) -> dict:
        return {
            "label": self.label, "n_examples": self.n_examples, "mean": self.mean,
            "median": self.median, "p10": self.p10, "p90": self.p90, "min": self.min,
            "max": self.max, "fraction_above_clip": self.fraction_above_clip,
            "l2_norm_clip": self.l2_norm_clip,
        }


def compute_per_example_gradient_norms(
    model, X: np.ndarray, y: np.ndarray, class_weight: dict[int, float], n_samples: int = 300
) -> np.ndarray:
    """Computes the true (unclipped) per-example gradient L2 norm for up to
    ``n_samples`` examples, using the SAME weighted binary cross-entropy loss
    DP training actually uses (``class_weight`` applied per-example, matching
    ``DPNeuralNetworkTrainer``'s training loop) -- so this measures exactly
    what DP-SGD's clipping operates on, not a simplified stand-in loss.
    """
    import tensorflow as tf
    from tensorflow import keras

    n = min(n_samples, len(X))
    bce = keras.losses.BinaryCrossentropy(reduction="none")
    norms = np.empty(n, dtype="float64")

    for i in range(n):
        x_i = tf.convert_to_tensor(X[i : i + 1])
        y_i = tf.convert_to_tensor(y[i : i + 1])
        weight = class_weight.get(int(y[i]), 1.0)
        with tf.GradientTape() as tape:
            pred = model(x_i, training=True)
            loss = bce(y_i, pred) * weight
        grads = tape.gradient(loss, model.trainable_variables)
        flat = tf.concat([tf.reshape(g, [-1]) for g in grads if g is not None], axis=0)
        norms[i] = float(tf.norm(flat).numpy())

    return norms


def summarize_gradient_norms(norms: np.ndarray, label: str, l2_norm_clip: float) -> GradientNormReport:
    return GradientNormReport(
        label=label,
        n_examples=len(norms),
        mean=float(np.mean(norms)),
        median=float(np.median(norms)),
        p10=float(np.percentile(norms, 10)),
        p90=float(np.percentile(norms, 90)),
        min=float(np.min(norms)),
        max=float(np.max(norms)),
        fraction_above_clip=float(np.mean(norms > l2_norm_clip)),
        l2_norm_clip=l2_norm_clip,
    )


def run_gradient_norm_diagnostic(
    model, X: np.ndarray, y: np.ndarray, class_weight: dict[int, float], l2_norm_clip: float, n_samples: int = 300
) -> dict[str, GradientNormReport]:
    """Runs the diagnostic separately for positive and negative examples
    (class_weight makes their raw gradient scales very different before
    clipping -- this is exactly the mechanism the DP report's "class_weight
    is neutralized by clipping" claim depends on, so it must be checked
    per-class, not just in aggregate).
    """
    positive_idx = np.where(y == 1)[0]
    negative_idx = np.where(y == 0)[0]

    rng = np.random.default_rng(42)
    pos_sample = rng.choice(positive_idx, size=min(n_samples, len(positive_idx)), replace=False)
    neg_sample = rng.choice(negative_idx, size=min(n_samples, len(negative_idx)), replace=False)

    pos_norms = compute_per_example_gradient_norms(model, X[pos_sample], y[pos_sample], class_weight, n_samples)
    neg_norms = compute_per_example_gradient_norms(model, X[neg_sample], y[neg_sample], class_weight, n_samples)
    all_norms = np.concatenate([pos_norms, neg_norms])

    reports = {
        "positive": summarize_gradient_norms(pos_norms, "positive", l2_norm_clip),
        "negative": summarize_gradient_norms(neg_norms, "negative", l2_norm_clip),
        "all": summarize_gradient_norms(all_norms, "all", l2_norm_clip),
    }
    for report in reports.values():
        logger.info(
            "Gradient norms (%s, n=%d): median=%.4f, p90=%.4f, max=%.4f, "
            "fraction_above_clip(%.2f)=%.1f%%",
            report.label, report.n_examples, report.median, report.p90, report.max,
            l2_norm_clip, report.fraction_above_clip * 100,
        )
    return reports
