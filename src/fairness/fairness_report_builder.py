"""Generates ``fairness_report.md`` and ``bias_findings.md`` from actual
computed results -- same philosophy as every prior module's report builder:
assembled from real run output, not static prose.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.config.config_loader import FairnessAnalysisConfig
from src.fairness.bias_detector import BiasFinding
from src.fairness.fairlearn_validation import FairlearnCrossCheckResult
from src.fairness.fairness_metrics import GroupMetrics, PairwiseFairnessMetrics
from src.fairness.statistical_tests import SignificanceTestResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AttributeFairnessResult:
    attribute_name: str
    description: str
    reference_group: str
    excluded_from_primary: bool
    group_metrics: dict[str, GroupMetrics]
    pairwise_metrics: dict[str, PairwiseFairnessMetrics]
    significance_result: Optional[SignificanceTestResult]
    bias_findings: list[BiasFinding]
    fairlearn_cross_check: list[FairlearnCrossCheckResult]


class FairnessReportBuilder:
    def build(
        self,
        model_name: str,
        dataset_version: str,
        results: list[AttributeFairnessResult],
        config: FairnessAnalysisConfig,
        output_dir: Path,
    ) -> None:
        self._write_fairness_report(model_name, dataset_version, results, config, output_dir)
        self._write_bias_findings(results, output_dir)

    def _write_fairness_report(self, model_name, dataset_version, results, config, output_dir) -> None:
        lines = [
            "# Module 5 — Fairness Analysis Report",
            "",
            f"- Model analyzed: **{model_name}** (Module 3's production model)",
            f"- Dataset version: `{dataset_version}`",
            "",
            "## Executive Summary",
            "",
            self._executive_summary(results),
            "",
            "## Methodology",
            "",
            "Group fairness metrics computed on Module 2's held-out test set (never used for training "
            "or model selection). Statistical Parity Difference, Disparate Impact Ratio, Equal "
            "Opportunity Difference, and Average Odds Difference are each reported with a 95% "
            "**stratified bootstrap confidence interval** "
            f"({config.statistics.bootstrap_iterations} resamples, drawn independently within each group "
            "to preserve group sizes), so a disparity can be judged statistically meaningful (CI excludes "
            "the null value) rather than read off a point estimate alone. Group-membership independence "
            "from predicted outcome is additionally tested via chi-square (or Fisher's exact test for "
            "2-group comparisons when Cochran's rule is violated) -- see `statistical_tests.py`'s module "
            "docstring for the full decision rule and its assumptions.",
            "",
            "## Protected Groups (Proxy Attributes — See Limitations)",
            "",
            "| Attribute | Reference Group | Primary | Description |",
            "|---|---|---|---|",
        ]
        for attr in config.protected_attributes:
            lines.append(f"| {attr.name} | {attr.reference_group} | {attr.primary} | {attr.description} |")

        lines += [
            "",
            "## Proxy Limitations — Read Before Interpreting Any Result Below",
            "",
            "**None of the attributes analyzed below are true demographic attributes.** The IEEE-CIS "
            "fraud dataset contains no age, gender, race, or other demographic fields. `card6` (debit "
            "vs. credit) and `card4` (card network) are payment-behavior proxies; `DeviceType` is a "
            "device-usage proxy with 80%+ missingness in the test set. Any disparity reported here "
            "reflects differences in **financial/behavioral patterns across these proxy groups**, not "
            "demographic discrimination. Treat findings as inputs to a business/compliance review, not "
            "as a demographic bias certification.",
            "",
        ]

        for result in results:
            lines += self._attribute_section(result, config)

        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "fairness_report.md").write_text("\n".join(lines), encoding="utf-8")
        logger.info("Fairness report written to %s", output_dir / "fairness_report.md")

    def _executive_summary(self, results: list[AttributeFairnessResult]) -> str:
        primary = next((r for r in results if not r.excluded_from_primary and r.pairwise_metrics), None)
        if primary is None:
            return "No primary attribute with a valid reference-group comparison was available."
        significant = [g for g, m in primary.pairwise_metrics.items() if m.spd_ci.excludes_null]
        lines = [
            f"Primary fairness attribute: **{primary.attribute_name}**. "
            f"{len(significant)} of {len(primary.pairwise_metrics)} group(s) show a statistically "
            f"significant selection-rate disparity (95% bootstrap CI excludes zero): "
            f"{significant if significant else 'none'}.",
        ]
        for g, m in primary.pairwise_metrics.items():
            lines.append(
                f"- '{g}' vs. reference '{m.reference_group}': SPD={m.statistical_parity_difference:+.4f}, "
                f"DIR={m.disparate_impact_ratio:.3f}, EOD={m.equal_opportunity_difference:+.4f}, "
                f"AOD={m.average_odds_difference:+.4f}."
            )
        return "\n".join(lines)

    def _attribute_section(self, result: AttributeFairnessResult, config: FairnessAnalysisConfig) -> list[str]:
        lines = [
            f"## Attribute: {result.attribute_name}" + (" (EXCLUDED FROM PRIMARY ANALYSIS)" if result.excluded_from_primary else ""),
            "",
            result.description,
            "",
            "### Group-wise Metrics",
            "",
            "| Group | n | Selection Rate | TPR (Recall) | FPR | FNR | Precision | F1 | Balanced Acc. | ROC-AUC | PR-AUC |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for g, m in result.group_metrics.items():
            roc = f"{m.roc_auc:.4f}" if m.roc_auc is not None else "N/A (single class)"
            pr = f"{m.pr_auc:.4f}" if m.pr_auc is not None else "N/A (single class)"
            lines.append(
                f"| {g} | {m.n:,} | {m.selection_rate:.4f} | {m.tpr:.4f} | {m.fpr:.4f} | {m.fnr:.4f} | "
                f"{m.precision:.4f} | {m.f1:.4f} | {m.balanced_accuracy:.4f} | {roc} | {pr} |"
            )

        if result.pairwise_metrics:
            lines += [
                "",
                "### Fairness Metrics (vs. reference group, with 95% bootstrap CI)",
                "",
                "| Group | SPD | SPD 95% CI | DIR | DIR 95% CI | EOD | EOD 95% CI | AOD | AOD 95% CI | Statistically Significant? |",
                "|---|---|---|---|---|---|---|---|---|---|",
            ]
            for g, m in result.pairwise_metrics.items():
                lines.append(
                    f"| {g} | {m.statistical_parity_difference:+.4f} | [{m.spd_ci.ci_lower:+.4f}, {m.spd_ci.ci_upper:+.4f}] | "
                    f"{m.disparate_impact_ratio:.3f} | [{m.dir_ci.ci_lower:.3f}, {m.dir_ci.ci_upper:.3f}] | "
                    f"{m.equal_opportunity_difference:+.4f} | [{m.eod_ci.ci_lower:+.4f}, {m.eod_ci.ci_upper:+.4f}] | "
                    f"{m.average_odds_difference:+.4f} | [{m.aod_ci.ci_lower:+.4f}, {m.aod_ci.ci_upper:+.4f}] | "
                    f"{'YES (SPD CI excludes 0)' if m.spd_ci.excludes_null else 'No'} |"
                )
        if result.significance_result:
            sr = result.significance_result
            lines += [
                "",
                f"### Significance Test: {sr.test_name.replace('_', ' ').title()}",
                f"- Statistic: {sr.statistic:.4f}, p-value: {sr.p_value:.6f}, alpha: {sr.alpha}",
                f"- Result: {'**Statistically significant**' if sr.significant else 'Not statistically significant'}",
                f"- {sr.notes}",
            ]
        if result.fairlearn_cross_check and result.fairlearn_cross_check[0].available:
            lines += ["", "### Fairlearn Cross-Validation", "", "| Metric | Own Value | Fairlearn Value | Abs. Diff. | Within Tolerance |", "|---|---|---|---|---|"]
            for c in result.fairlearn_cross_check:
                lines.append(f"| {c.metric_name} | {c.own_value:.6f} | {c.fairlearn_value:.6f} | {c.absolute_difference:.2e} | {c.within_tolerance} |")
        elif result.fairlearn_cross_check:
            lines += ["", "### Fairlearn Cross-Validation", "", result.fairlearn_cross_check[0].notes]

        lines.append("")
        return lines

    def _write_bias_findings(self, results: list[AttributeFairnessResult], output_dir: Path) -> None:
        lines = ["# Module 5 — Bias Findings", "", "Automatically generated findings from the computed fairness metrics.", ""]
        for result in results:
            lines.append(f"## {result.attribute_name}")
            lines.append("")
            for finding in result.bias_findings:
                lines.append(f"- **[{finding.severity.upper()}]** {finding.description}")
            lines.append("")
        (output_dir / "bias_findings.md").write_text("\n".join(lines), encoding="utf-8")
        logger.info("Bias findings written to %s", output_dir / "bias_findings.md")
