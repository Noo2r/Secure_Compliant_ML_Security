"""Generates Module 3's Model Development Report, Model Card, and
Hyperparameter Tuning Report from actual run results -- same philosophy as
Module 2's ``FeatureEngineeringReportBuilder``: assembled from real numbers
produced by this run, not static prose.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.evaluation.comparison import BestModelSelection
from src.models.train import ModelTrainingResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ModelDevelopmentReportBuilder:
    def build(
        self,
        results: list[ModelTrainingResult],
        leaderboard: pd.DataFrame,
        selection: BestModelSelection,
        statistical_comparison: dict,
        dataset_version: str,
        azure_model_id: str | None,
        output_dir: Path,
    ) -> None:
        self._write_model_development_report(results, leaderboard, selection, statistical_comparison, dataset_version, output_dir)
        self._write_model_card(results, selection, dataset_version, azure_model_id, output_dir)
        self._write_hyperparameter_tuning_report(results, output_dir)

    def _write_model_development_report(
        self, results, leaderboard, selection, statistical_comparison, dataset_version, output_dir
    ) -> None:
        lines = [
            "# Module 3 — Model Development Report",
            "",
            f"- Dataset version: `{dataset_version}`",
            f"- Candidate models compared: {[r.model_name for r in results]}",
            "",
            "## Leaderboard (ranked by holdout PR-AUC)",
            "",
            leaderboard.to_markdown(index=False),
            "",
            "## Best model selection",
            f"**{selection.model_name}** (leaderboard rank {selection.leaderboard_rank})",
            "",
            selection.justification,
            "",
            "## Statistical comparison (top 2 models, paired Wilcoxon over CV folds)",
            "",
            f"```\n{statistical_comparison}\n```",
            "",
            "## Per-model operational metrics",
            "",
            "| Model | Recall @ Precision target | Precision@K (first configured K) |",
            "|---|---|---|",
        ]
        for r in results:
            rp = r.operational_metrics["recall_at_precision"]
            pk = r.operational_metrics["precision_at_k"][0] if r.operational_metrics["precision_at_k"] else {}
            lines.append(
                f"| {r.model_name} | recall={rp['recall']:.4f} at precision={rp['achieved_precision']:.4f} "
                f"(target {rp['min_precision_target']:.2f}, met={rp['target_met']}) | "
                f"k={pk.get('k')}, precision={pk.get('precision_at_k', float('nan')):.4f} |"
            )
        (output_dir / "model_development_report.md").write_text("\n".join(lines), encoding="utf-8")
        logger.info("Model development report written to %s", output_dir / "model_development_report.md")

    def _write_model_card(self, results, selection, dataset_version, azure_model_id, output_dir) -> None:
        best = next(r for r in results if r.model_name == selection.model_name)
        lines = [
            "# Model Card — Fraud Detection Model",
            "",
            "## Purpose and intended use",
            "Binary fraud/not-fraud classification of IEEE-CIS style card transactions, "
            "for a regulated financial fraud-detection pipeline (Milestone 2 of the "
            "Secure & Compliant ML Security Pipeline project). Intended to score "
            "transactions and flag likely fraud for review, not for fully automated "
            "adverse action without human review.",
            "",
            f"## Model type\n{selection.model_name}",
            f"## Dataset version\n`{dataset_version}`",
            "",
            "## Training data",
            "Module 2's time-aware, feature-engineered, feature-selected, preprocessed "
            "training split. Encrypted/PII columns (Module 1) are never used as features. "
            "TransactionID and fairness sensitive attributes (card6, card4, DeviceType) are "
            "preserved as non-feature metadata, never as model input.",
            "",
            "## Performance (holdout test set)",
            f"- PR-AUC: {best.holdout_metrics.pr_auc:.4f}",
            f"- ROC-AUC: {best.holdout_metrics.roc_auc:.4f}",
            f"- F1: {best.holdout_metrics.f1:.4f} (at decision threshold {best.threshold_decision.threshold:.4f})",
            f"- Precision: {best.holdout_metrics.precision:.4f}",
            f"- Recall: {best.holdout_metrics.recall:.4f}",
            "",
            "## Known limitations",
            "- Trained on synthetic-PII-augmented IEEE-CIS data via Module 1's reproduction "
            "pipeline, not Yara's original encrypted artifact.",
            "- Fairness analysis (Module 5) not yet performed as of this report.",
            "- Differential privacy training (Module 4) not yet applied to this model version.",
            "- Adversarial robustness (Module 6) not yet assessed.",
            "",
            f"## Azure ML registration\n{azure_model_id or 'Not registered (no Azure ML credentials configured).'}",
        ]
        (output_dir / "model_card.md").write_text("\n".join(lines), encoding="utf-8")
        logger.info("Model card written to %s", output_dir / "model_card.md")

    def _write_hyperparameter_tuning_report(self, results, output_dir) -> None:
        lines = ["# Module 3 — Hyperparameter Tuning Report", ""]
        for r in results:
            tr = r.tuning_result
            lines += [
                f"## {r.model_name}",
                f"- Trials completed: {tr.n_trials_completed}",
                f"- Tuning wall-clock: {tr.tuning_seconds:.1f}s",
                f"- Best CV PR-AUC: {tr.best_cv_score:.4f} (fold scores: {[round(s, 4) for s in tr.cv_fold_scores]})",
                f"- Best hyperparameters: `{tr.best_params}`",
                "",
            ]
        (output_dir / "hyperparameter_tuning_report.md").write_text("\n".join(lines), encoding="utf-8")
        logger.info("Hyperparameter tuning report written to %s", output_dir / "hyperparameter_tuning_report.md")
