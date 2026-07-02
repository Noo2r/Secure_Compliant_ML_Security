"""Statistical significance testing for group disparities.

Two tests, chosen by an explicit, documented decision rule rather than
always defaulting to one:

* **Chi-square test of independence** (`scipy.stats.chi2_contingency`) --
  tests whether predicted-outcome distribution is independent of group
  membership across a [group x predicted_label] contingency table. Valid
  under Cochran's rule: at least 80% of cells must have expected count >= 5
  (a standard, citable threshold, not invented here).
* **Fisher's exact test** (`scipy.stats.fisher_exact`) -- exact (no
  large-sample approximation), but scipy only supports 2x2 tables. Used
  automatically as the fallback for 2-group comparisons when Cochran's rule
  is violated.

Neither test is a fairness metric by itself -- they answer "is this
difference in selection rate/TPR/FPR distinguishable from sampling noise?",
a different (and complementary) question from *how large* the disparity is,
which the bootstrap confidence intervals in :mod:`fairness_metrics` answer.

**Assumptions and limitations, stated once here rather than scattered:**
both tests assume independent observations. Transactions are treated as
independent units (the unit this entire project's row-level analysis
operates on); if multiple transactions from the same card/account are
correlated, both tests' p-values are somewhat too optimistic (a standard,
known limitation of transaction-level significance testing without
account-level clustering correction, which this project's dataset does not
reliably support). Multi-group (>2 category) tables can only use chi-square
-- scipy has no built-in multi-group exact test, so Cochran's-rule
violations for >2 groups are reported as a validity caveat, not silently
ignored.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, fisher_exact

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class SignificanceTestResult:
    test_name: str  # "chi_square" | "fishers_exact"
    statistic: Optional[float]
    p_value: float
    alpha: float
    significant: bool
    cochrans_rule_satisfied: bool
    min_expected_cell_count: float
    contingency_table: list
    notes: str

    def to_dict(self) -> dict:
        return asdict(self)


def _cochrans_rule_satisfied(expected: np.ndarray, min_expected_count: float) -> bool:
    """At least 80% of cells must have expected count >= threshold (Cochran 1954)."""
    return float(np.mean(expected >= min_expected_count)) >= 0.8


def run_group_disparity_test(
    group_labels: np.ndarray,
    predicted_labels: np.ndarray,
    alpha: float,
    min_expected_cell_count: float,
) -> SignificanceTestResult:
    """Tests whether predicted-positive rate is independent of group membership.

    Builds a [group x predicted_label] contingency table from ALL groups
    present in ``group_labels`` (NaN/missing excluded). Automatically uses
    Fisher's exact test for a 2-group table when Cochran's rule is violated;
    otherwise uses chi-square, always reporting whether the rule held.
    """
    valid_mask = ~pd.isna(group_labels)
    groups = group_labels[valid_mask]
    preds = predicted_labels[valid_mask]

    unique_groups = sorted(np.unique(groups).tolist())
    table = np.array([
        [int(np.sum((groups == g) & (preds == 0))), int(np.sum((groups == g) & (preds == 1)))]
        for g in unique_groups
    ])

    chi2, p_chi2, dof, expected = chi2_contingency(table, correction=False)
    rule_satisfied = _cochrans_rule_satisfied(expected, min_expected_cell_count)

    if len(unique_groups) == 2 and not rule_satisfied:
        odds_ratio, p_value = fisher_exact(table)
        result = SignificanceTestResult(
            test_name="fishers_exact", statistic=float(odds_ratio), p_value=float(p_value), alpha=alpha,
            significant=bool(p_value < alpha), cochrans_rule_satisfied=rule_satisfied,
            min_expected_cell_count=float(expected.min()), contingency_table=table.tolist(),
            notes=(
                "Cochran's rule violated (some expected cell counts < "
                f"{min_expected_cell_count}) -- used Fisher's exact test (exact, no "
                "large-sample assumption) instead of chi-square."
            ),
        )
    else:
        notes = "Cochran's rule satisfied -- chi-square test of independence is valid."
        if not rule_satisfied:
            notes = (
                f"WARNING: Cochran's rule violated for a {len(unique_groups)}-group table "
                "(min expected cell count "
                f"{expected.min():.2f} < {min_expected_cell_count}), but scipy has no "
                "multi-group exact test -- chi-square result reported with reduced confidence, "
                "not suppressed."
            )
            logger.warning(notes)
        result = SignificanceTestResult(
            test_name="chi_square", statistic=float(chi2), p_value=float(p_chi2), alpha=alpha,
            significant=bool(p_chi2 < alpha), cochrans_rule_satisfied=rule_satisfied,
            min_expected_cell_count=float(expected.min()), contingency_table=table.tolist(), notes=notes,
        )

    logger.info(
        "Significance test (%s): statistic=%.4f p=%.6f significant=%s (alpha=%.3f, groups=%s)",
        result.test_name, result.statistic or float("nan"), result.p_value, result.significant, alpha, unique_groups,
    )
    return result
