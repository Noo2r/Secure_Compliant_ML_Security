"""Differential privacy budget (epsilon, delta) accounting for DP-SGD training.

Wraps TensorFlow Privacy's RDP accountant (``compute_dp_sgd_privacy_lib``).
Reports the epsilon that actually corresponds to how this project trains
models -- standard epoch-based shuffled mini-batch training via Keras
``model.fit()``, **not** Poisson/random per-step subsampling. TF-Privacy's
own accountant computes both figures and explicitly warns that the
Poisson-sampling epsilon is optimistic and does not apply to a training loop
that doesn't actually use Poisson sampling. Reporting only the smaller,
Poisson-assumption epsilon (as informal DP-SGD write-ups sometimes do) would
overstate this model's real privacy guarantee, so both are recorded here and
the non-subsampling epsilon is treated as authoritative throughout this
module's reports and MLflow logging.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from src.privacy import tf_privacy_compat  # noqa: F401 -- must precede tensorflow_privacy import
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class PrivacyBudget:
    """The result of a single (epsilon, delta) accounting computation."""

    epsilon: float
    """Epsilon assuming each example occurs once per epoch (matches this
    project's actual shuffled-epoch training loop) -- the authoritative,
    conservative figure reported as "the" epsilon everywhere else in Module 4."""

    epsilon_poisson_assumption: float
    """Epsilon under the (here, inapplicable) assumption of Poisson/random
    per-step subsampling. Recorded for transparency and comparison only --
    NOT the guarantee this project's training loop actually provides."""

    delta: float
    noise_multiplier: float
    num_examples: int
    batch_size: int
    epochs: int
    statement: str
    """Full human-readable statement from TF-Privacy, included verbatim in
    generated reports for auditability."""

    def to_dict(self) -> dict:
        return asdict(self)


class PrivacyAccountant:
    """Computes (epsilon, delta) for a given DP-SGD training configuration."""

    def compute(
        self, num_examples: int, batch_size: int, noise_multiplier: float, epochs: int, delta: float
    ) -> PrivacyBudget:
        from tensorflow_privacy.privacy.analysis.compute_dp_sgd_privacy_lib import (
            _compute_dp_sgd_example_privacy,
            compute_dp_sgd_privacy_statement,
        )

        statement = compute_dp_sgd_privacy_statement(
            number_of_examples=num_examples,
            batch_size=batch_size,
            noise_multiplier=noise_multiplier,
            num_epochs=epochs,
            delta=delta,
        )
        # `_compute_dp_sgd_example_privacy` is a private (leading-underscore)
        # function. It is used deliberately: TF-Privacy 0.8.11's PUBLIC API
        # exposes epsilon only as (a) embedded text inside the statement
        # above, or (b) via the explicitly-deprecated `compute_dp_sgd_privacy`,
        # which the library itself warns "does not account for doubling of
        # sensitivity with microbatching" -- i.e. would silently under-report
        # epsilon for this project's per-example-microbatch configuration.
        # This private function is the exact function the public statement
        # text is generated from (verified by cross-checking its output
        # against the statement's printed values), so it is the correct,
        # not merely convenient, choice for a numeric epsilon.
        epsilon = _compute_dp_sgd_example_privacy(
            num_epochs=epochs,
            noise_multiplier=noise_multiplier,
            example_delta=delta,
            used_microbatching=True,
        )
        epsilon_poisson = _compute_dp_sgd_example_privacy(
            num_epochs=epochs,
            noise_multiplier=noise_multiplier,
            example_delta=delta,
            used_microbatching=True,
            poisson_subsampling_probability=batch_size / num_examples,
        )

        budget = PrivacyBudget(
            epsilon=epsilon,
            epsilon_poisson_assumption=epsilon_poisson,
            delta=delta,
            noise_multiplier=noise_multiplier,
            num_examples=num_examples,
            batch_size=batch_size,
            epochs=epochs,
            statement=statement,
        )
        logger.info(
            "Privacy budget computed: epsilon=%.4f (epsilon_poisson_assumption=%.4f, "
            "NOT applicable to this training loop), delta=%.2e, noise_multiplier=%.3f",
            budget.epsilon, budget.epsilon_poisson_assumption, budget.delta, budget.noise_multiplier,
        )
        return budget
