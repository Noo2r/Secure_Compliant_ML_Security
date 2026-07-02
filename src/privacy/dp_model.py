"""Normal vs. Differentially-Private Neural Network training on an
IDENTICAL architecture -- only the optimizer differs between the two.

Reuses Module 3's exact architecture-construction method
(``KerasClassifierWrapper._build_model``) for both variants, so "only the
optimizer changes" is true by construction, not merely by intention.
Module 3's file (``src/models/keras_wrapper.py``) is never modified --
this module calls that method from the outside, exactly like Module 3
itself does internally.

**Class-imbalance handling under DP-SGD -- an important, honestly-documented
limitation, not a hidden footgun:** Module 3's Normal NN applies
``class_weight`` to counter the ~3.5% positive rate, and this module passes
the identical ``class_weight`` through to DP training for consistency. But
its effect is structurally different under DP-SGD: per-example gradient
clipping projects each example's gradient onto a fixed L2-norm ball
*after* it has been scaled by its class weight. If a weighted gradient's
norm already exceeds ``l2_norm_clip`` (the common case for a small clip
norm such as 1.0, which is required to keep the noise-to-signal ratio
reasonable), clipping preserves direction but caps magnitude -- so scaling
the same vector by any positive constant before clipping yields the
*identical* post-clip result. In that regime, ``class_weight`` has **no
effect** on the clipped gradient DP-SGD actually applies, unlike normal
training where it directly reweights the loss surface. This is verified
empirically (not just theorized) in Module 4's evaluation -- see the
generated DP report's privacy-utility analysis section.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from src.privacy import tf_privacy_compat  # noqa: F401 -- must precede tensorflow import
from src.models.keras_wrapper import KerasClassifierWrapper
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TrainingRunResult:
    """One trained model (either variant) plus its training history/cost."""

    variant: str  # "normal" | "dp"
    model: Any  # trained Keras model (tf_keras, per the compatibility shim)
    history: dict[str, list[float]]  # per-epoch metric history, e.g. {"loss": [...], "pr_auc": [...]}
    train_seconds: float
    initial_weights_checksum: float
    """Sum of absolute initial weight values, recorded before training starts,
    to verify (not merely assume) that both variants began from identical
    initial weights -- see :meth:`DPNeuralNetworkTrainer._build_architecture`."""


class DPNeuralNetworkTrainer:
    """Trains the Normal and DP variants of Module 3's tuned NN architecture.

    Parameters
    ----------
    architecture_params:
        ``{"n_layers", "units", "dropout", "learning_rate"}`` -- read from
        Module 3's already-tuned Neural Network hyperparameters by the
        caller (``scripts/run_module4.py``), not redefined here.
    class_weight_positive:
        Weight applied to the positive (fraud) class, matching Module 3's
        ``scale_pos_weight``-style imbalance handling (see module docstring
        for its documented, limited effect under DP-SGD).
    random_state:
        Seed used for both variants' weight initialization -- see
        :meth:`_build_architecture` for how identical initial weights are
        obtained and verified.
    """

    def __init__(self, architecture_params: dict, class_weight_positive: float, random_state: int = 42) -> None:
        self.architecture_params = architecture_params
        self.class_weight_positive = class_weight_positive
        self.random_state = random_state
        # Populated by the first _build_architecture() call for a given
        # n_features and reused by every subsequent call -- see that
        # method's docstring for why this is necessary, not merely tidy.
        self._reference_weights_cache: dict[int, list] = {}

    def _build_architecture(self, n_features: int) -> Any:
        """Builds one instance of Module 3's exact layer architecture, with
        initial weights IDENTICAL across every call from this trainer
        instance (normal, DP, and every sweep point).

        The first implementation of this method relied on calling
        ``tf.random.set_seed(self.random_state)`` before each build,
        assuming that would reproduce identical weights across separate
        calls. **This was verified, empirically, to be false**: TF derives
        each random op's actual seed from both the global seed AND a
        per-process op-creation counter that keeps advancing across
        separate ``_build_model()`` calls, so two "identically seeded"
        builds produce measurably different initial weights (caught by
        this module's own unit test comparing weight checksums -- not a
        hypothetical concern). Fixed here by building once, capturing the
        resulting weights via ``get_weights()``, and explicitly applying
        them to every subsequent build via ``set_weights()`` -- a
        correctness guarantee that does not depend on TensorFlow's RNG
        implementation details at all.
        """
        wrapper = KerasClassifierWrapper(
            n_layers=self.architecture_params["n_layers"],
            units=self.architecture_params["units"],
            dropout=self.architecture_params["dropout"],
            learning_rate=self.architecture_params["learning_rate"],
            random_state=self.random_state,
        )
        model = wrapper._build_model(n_features)  # noqa: SLF001 -- deliberate reuse, see module docstring

        if n_features not in self._reference_weights_cache:
            self._reference_weights_cache[n_features] = model.get_weights()
        else:
            model.set_weights(self._reference_weights_cache[n_features])
        return model

    @staticmethod
    def _weights_checksum(model: Any) -> float:
        return float(sum(np.abs(w).sum() for w in model.get_weights()))

    @staticmethod
    def _truncate_to_batch_multiple(X: np.ndarray, y: np.ndarray, batch_size: int) -> tuple[np.ndarray, np.ndarray]:
        """Drops the ragged final batch so every batch has exactly ``batch_size`` rows.

        Required for DP training: TF-Privacy's per-example microbatching
        (``num_microbatches == batch_size``) reshapes each batch's
        per-example losses into ``[num_microbatches, -1]``, which fails with
        an ``InvalidArgumentError`` whenever the dataset size isn't evenly
        divisible by ``batch_size`` -- Keras's default last-batch behavior
        delivers a smaller, ragged final batch, which breaks that reshape.
        Verified directly against the real dataset (401,567 rows / 256 =
        1568 batches + a 159-row remainder that crashed training), not
        assumed. Applied to BOTH variants, not just DP, so Normal and DP
        train on identically-sized data -- a fairness property, not just a
        DP requirement, since dropping ~0.06% of rows (at most
        ``batch_size - 1`` out of ~400K here) has no material effect on
        either model but keeps the comparison exact.
        """
        usable_rows = (len(X) // batch_size) * batch_size
        if usable_rows == len(X):
            return X, y
        logger.info(
            "Truncating %d rows to %d (dropping %d-row ragged remainder) so every "
            "batch has exactly batch_size=%d rows.",
            len(X), usable_rows, len(X) - usable_rows, batch_size,
        )
        return X[:usable_rows], y[:usable_rows]

    def train_normal(self, X_train: np.ndarray, y_train: np.ndarray, batch_size: int, epochs: int) -> TrainingRunResult:
        """Trains the Normal (non-private) variant -- Module 3's architecture, Adam optimizer."""
        X_train, y_train = self._truncate_to_batch_multiple(X_train, y_train, batch_size)
        model = self._build_architecture(X_train.shape[1])
        checksum = self._weights_checksum(model)

        start = time.monotonic()
        history = model.fit(
            X_train, y_train,
            batch_size=batch_size, epochs=epochs,
            class_weight={0: 1.0, 1: self.class_weight_positive},
            verbose=0,
        )
        elapsed = time.monotonic() - start

        logger.info("Normal NN trained: %d epochs, %.1fs, final loss=%.4f",
                    epochs, elapsed, history.history["loss"][-1])
        return TrainingRunResult(
            variant="normal", model=model, history=history.history,
            train_seconds=elapsed, initial_weights_checksum=checksum,
        )

    def train_dp(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        batch_size: int,
        epochs: int,
        l2_norm_clip: float,
        noise_multiplier: float,
        microbatches: int,
    ) -> TrainingRunResult:
        """Trains the DP variant -- identical architecture, DP-Adam optimizer.

        ``microbatches`` MUST equal ``batch_size`` for true per-example
        gradient clipping (TF-Privacy's own semantics -- see
        ``src/config/config.yaml``'s ``differential_privacy.microbatches``
        comment for the verified explanation) and must exactly match the
        ``batch_size`` this method passes to ``model.fit()``, or TF-Privacy
        raises a shape error at the first training step (verified while
        building this module, not assumed).
        """
        from tensorflow import keras
        from tensorflow_privacy.privacy.optimizers.dp_optimizer_keras import DPKerasAdamOptimizer

        if batch_size % microbatches != 0:
            raise ValueError(
                f"microbatches ({microbatches}) must evenly divide batch_size ({batch_size})"
            )

        X_train, y_train = self._truncate_to_batch_multiple(X_train, y_train, batch_size)
        model = self._build_architecture(X_train.shape[1])
        checksum = self._weights_checksum(model)

        dp_optimizer = DPKerasAdamOptimizer(
            l2_norm_clip=l2_norm_clip,
            noise_multiplier=noise_multiplier,
            num_microbatches=microbatches,
            learning_rate=self.architecture_params["learning_rate"],
        )
        # DP-SGD requires the UNREDUCED per-example loss (reduction="none")
        # so gradients can be computed and clipped per example before the DP
        # optimizer aggregates them -- this is a hard requirement of
        # TF-Privacy's optimizer, not a style choice.
        model.compile(
            optimizer=dp_optimizer,
            loss=keras.losses.BinaryCrossentropy(reduction="none"),
            metrics=[keras.metrics.AUC(name="pr_auc", curve="PR")],
        )

        start = time.monotonic()
        history = model.fit(
            X_train, y_train,
            batch_size=batch_size, epochs=epochs,
            class_weight={0: 1.0, 1: self.class_weight_positive},
            verbose=0,
        )
        elapsed = time.monotonic() - start

        logger.info("DP NN trained: %d epochs, %.1fs, final loss=%.4f, "
                    "l2_norm_clip=%.3f, noise_multiplier=%.3f, microbatches=%d",
                    epochs, elapsed, history.history["loss"][-1], l2_norm_clip, noise_multiplier, microbatches)
        return TrainingRunResult(
            variant="dp", model=model, history=history.history,
            train_seconds=elapsed, initial_weights_checksum=checksum,
        )
