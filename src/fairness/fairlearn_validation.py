"""Cross-validates this project's own fairness metric implementations against
Fairlearn's independent implementation, on the real data.

This is a validation step, not a dependency this project's core pipeline
relies on: :mod:`fairness_metrics` and :mod:`statistical_tests` are fully
self-contained and were built first. Fairlearn is used here purely to answer
"does an independent, widely-used library agree with our numbers?" -- if
Fairlearn is not installed, this check is skipped with a clear log message,
never a hard failure, since it is a validation convenience, not a
correctness dependency.

Why not just use Fairlearn directly for the whole module: this project
needs Average Odds Difference (AIF360's definition) and bootstrap
confidence intervals + significance testing, which are not both available
in Fairlearn's metric set, and keeping full control over edge-case handling
(empty groups, single-class groups, NaN groups -- all explicitly required
test cases) is easier in an implementation this project owns outright than
one layered on top of a third-party API. Fairlearn is used only for the
subset of metrics it *does* implement (demographic parity difference/ratio,
selection rate), as an independent check.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

import numpy as np

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class FairlearnCrossCheckResult:
    available: bool
    metric_name: str
    own_value: Optional[float] = None
    fairlearn_value: Optional[float] = None
    absolute_difference: Optional[float] = None
    within_tolerance: Optional[bool] = None
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def is_fairlearn_available() -> bool:
    try:
        import fairlearn  # noqa: F401
        return True
    except ImportError:
        return False


def cross_check_against_fairlearn(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    group_labels: np.ndarray,
    own_selection_rate_by_group: dict[str, float],
    own_spd: float,
    own_dir: float,
    group: str,
    reference_group: str,
    tolerance: float,
) -> list[FairlearnCrossCheckResult]:
    """Compares this project's own SPD/DIR/selection-rate numbers against
    Fairlearn's ``demographic_parity_difference``/``demographic_parity_ratio``/
    ``selection_rate`` on the SAME (y_true, y_pred, group_labels) inputs.
    """
    if not is_fairlearn_available():
        logger.warning("Fairlearn not installed -- skipping cross-validation (not a hard failure).")
        return [FairlearnCrossCheckResult(available=False, metric_name="all", notes="fairlearn not installed")]

    from fairlearn.metrics import (
        demographic_parity_difference,
        demographic_parity_ratio,
        selection_rate,
        MetricFrame,
    )

    mask = np.isin(group_labels, [group, reference_group])
    y_true_masked, y_pred_masked, groups_masked = y_true[mask], y_pred[mask], group_labels[mask]

    fairlearn_spd = float(demographic_parity_difference(y_true_masked, y_pred_masked, sensitive_features=groups_masked))
    fairlearn_dir = float(demographic_parity_ratio(y_true_masked, y_pred_masked, sensitive_features=groups_masked))
    frame = MetricFrame(metrics=selection_rate, y_true=y_true_masked, y_pred=y_pred_masked, sensitive_features=groups_masked)
    fairlearn_selection_rates = frame.by_group.to_dict()

    results = []

    # SPD: Fairlearn's demographic_parity_difference is defined as
    # max(selection_rate) - min(selection_rate) across the given groups --
    # an UNSIGNED, absolute quantity, unlike this project's SIGNED
    # (group - reference) SPD. Compare absolute values, documented explicitly
    # so an apparent "mismatch" isn't mistaken for a bug.
    abs_diff_spd = abs(abs(own_spd) - fairlearn_spd)
    results.append(FairlearnCrossCheckResult(
        available=True, metric_name="statistical_parity_difference (compared as |own_SPD| vs Fairlearn's unsigned max-min difference)",
        own_value=abs(own_spd), fairlearn_value=fairlearn_spd, absolute_difference=abs_diff_spd,
        within_tolerance=abs_diff_spd <= tolerance,
        notes="Fairlearn's demographic_parity_difference is unsigned (max-min); this project's SPD is signed (group-reference). Compared as absolute values.",
    ))

    # DIR: Fairlearn's demographic_parity_ratio = min(selection_rate) / max(selection_rate)
    # (always <= 1, direction-agnostic), vs. this project's DIR = group/reference
    # (can be >1 or <1 depending on which is larger). Compare the "always <=1" form.
    own_dir_normalized = min(own_dir, 1 / own_dir) if own_dir > 0 else float("nan")
    abs_diff_dir = abs(own_dir_normalized - fairlearn_dir)
    results.append(FairlearnCrossCheckResult(
        available=True, metric_name="disparate_impact_ratio (compared in Fairlearn's normalized min/max form)",
        own_value=own_dir_normalized, fairlearn_value=fairlearn_dir, absolute_difference=abs_diff_dir,
        within_tolerance=abs_diff_dir <= tolerance,
        notes="Fairlearn's demographic_parity_ratio = min(rate)/max(rate) (direction-agnostic); this project's DIR = group/reference. Compared in the normalized form.",
    ))

    for g in (group, reference_group):
        own_rate = own_selection_rate_by_group.get(g)
        fl_rate = fairlearn_selection_rates.get(g)
        if own_rate is None or fl_rate is None:
            continue
        diff = abs(own_rate - fl_rate)
        results.append(FairlearnCrossCheckResult(
            available=True, metric_name=f"selection_rate[{g}]",
            own_value=own_rate, fairlearn_value=float(fl_rate), absolute_difference=diff,
            within_tolerance=diff <= tolerance, notes="Directly comparable -- same definition in both implementations.",
        ))

    for r in results:
        logger.info(
            "Fairlearn cross-check [%s]: own=%s fairlearn=%s diff=%s within_tolerance=%s",
            r.metric_name, r.own_value, r.fairlearn_value, r.absolute_difference, r.within_tolerance,
        )
    return results
