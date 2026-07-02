"""Generates the Module 4 Differential Privacy report from actual run
results -- same philosophy as Module 2/3's report builders: assembled from
real numbers produced by this run, not static prose.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.privacy.dp_evaluation import DPComparisonResult
from src.privacy.dp_model import TrainingRunResult
from src.privacy.privacy_accountant import PrivacyBudget
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DPReportBuilder:
    def build(
        self,
        architecture_params: dict,
        batch_size: int,
        epochs: int,
        l2_norm_clip: float,
        noise_multiplier: float,
        microbatches: int,
        privacy_budget: PrivacyBudget,
        normal_result: TrainingRunResult,
        dp_result: TrainingRunResult,
        comparison: DPComparisonResult,
        sweep_df: pd.DataFrame,
        dataset_version: str,
        output_path: Path,
    ) -> None:
        lines = [
            "# Module 4 — Differential Privacy Report",
            "",
            f"- Dataset version: `{dataset_version}`",
            "",
            "## 1. Architecture",
            f"- Layers: {architecture_params['n_layers']} hidden Dense layer(s) of "
            f"{architecture_params['units']} units (ReLU), dropout={architecture_params['dropout']:.3f}, "
            "sigmoid output.",
            "- Identical architecture and initial weights for both Normal and DP variants "
            f"(verified: initial weight checksums {normal_result.initial_weights_checksum:.6f} vs "
            f"{dp_result.initial_weights_checksum:.6f} -- "
            f"{'MATCH' if abs(normal_result.initial_weights_checksum - dp_result.initial_weights_checksum) < 1e-6 else 'DO NOT MATCH -- see limitations'}).",
            "- No BatchNormalization (incompatible with per-example gradient computation DP-SGD requires).",
            "- Reused directly from Module 3's `KerasClassifierWrapper._build_model` — not reimplemented.",
            "",
            "## 2. Optimizer",
            "- Normal: `keras.optimizers.Adam` (Module 3's tuned learning rate "
            f"{architecture_params['learning_rate']:.6f}).",
            "- DP: `tensorflow_privacy.DPKerasAdamOptimizer` (same base optimizer family + "
            "per-example gradient clipping + Gaussian noise) -- the only difference between the two runs.",
            "",
            "## 3. Differential Privacy Parameters",
            f"- Noise multiplier: {noise_multiplier}",
            f"- L2 gradient clipping norm: {l2_norm_clip}",
            f"- Microbatches: {microbatches} (== batch_size => true per-example clipping, "
            "not batch-averaged clipping -- see config.yaml's documented verification of this semantic)",
            f"- Batch size: {batch_size}",
            f"- Epochs: {epochs}",
            f"- Delta: {privacy_budget.delta:.2e}",
            "",
            "## 4. Privacy Accounting",
            f"- **Epsilon (matches actual training loop -- shuffled epochs, no Poisson subsampling): "
            f"{privacy_budget.epsilon:.4f}**",
            f"- Epsilon under the (inapplicable) Poisson-subsampling assumption: "
            f"{privacy_budget.epsilon_poisson_assumption:.4f} — NOT the guarantee this training actually provides; "
            "recorded for transparency only.",
            "",
            "Full TensorFlow Privacy accountant statement:",
            "```",
            privacy_budget.statement,
            "```",
            "",
            "## 5. Training Time",
            f"- Normal NN: {normal_result.train_seconds:.2f}s",
            f"- DP NN: {dp_result.train_seconds:.2f}s "
            f"({dp_result.train_seconds / normal_result.train_seconds:.2f}x the Normal NN's time)",
            "",
            "## 6. Evaluation Metrics (holdout test set)",
            "",
            "| Metric | Normal | DP | Delta (Normal - DP) |",
            "|---|---|---|---|",
        ]
        for field in ("accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"):
            n_val = getattr(comparison.normal_metrics, field)
            d_val = getattr(comparison.dp_metrics, field)
            lines.append(f"| {field} | {n_val:.4f} | {d_val:.4f} | {comparison.metric_deltas[field]:.4f} |")

        lines += [
            "",
            "### Confusion matrices (at each model's own optimized threshold)",
            "",
            f"- Normal (threshold={comparison.normal_threshold.threshold:.4f}): {comparison.normal_confusion_matrix}",
            f"- DP (threshold={comparison.dp_threshold.threshold:.4f}): {comparison.dp_confusion_matrix}",
            "",
            "## 7. Privacy-Utility Analysis",
            "",
            comparison.explanation,
            "",
            "### Noise multiplier sweep (privacy-utility curve data)",
            "",
            sweep_df.to_markdown(index=False) if not sweep_df.empty else "_Sweep not run._",
            "",
            "## 8. Advantages of the DP Approach",
            "- Provides a formal, mathematically-provable bound (epsilon, delta) on how much any single "
            "training example can influence the trained model -- normal training provides no such guarantee "
            "and is vulnerable to membership-inference and model-inversion attacks that DP-SGD is specifically "
            "designed to resist.",
            "- The privacy guarantee holds regardless of what an adversary already knows or what auxiliary "
            "data they have access to (a worst-case guarantee, not a statistical average-case one).",
            "",
            "## 9. Limitations",
            "- Utility cost is real and measured above, not hypothetical -- see Section 6.",
            "- `class_weight` for class-imbalance correction is structurally weakened under DP-SGD's "
            "per-example gradient clipping (see `src/privacy/dp_model.py` module docstring for the full "
            "mechanistic explanation) -- this is a genuine tension between fairness/imbalance handling and "
            "DP training on this dataset, not fully resolved here.",
            "- The reported epsilon assumes the accountant's modeling of the training process (shuffled "
            "epochs, Gaussian mechanism) exactly matches what Keras's `model.fit()` actually does step by "
            "step; this project did not independently re-derive or audit TF-Privacy's accounting math.",
            "- Both Normal and DP variants inherit Module 3's Neural Network architecture, which was the "
            "**weakest of Module 3's five candidates** (holdout PR-AUC 0.093 vs. LightGBM's 0.487) -- so this "
            "entire Normal-vs-DP comparison is built on a mediocre base model, not this project's best classifier.",
            "- `tensorflow-privacy` required three separate compatibility workarounds to run on this "
            "project's TensorFlow 2.20 installation (see `src/privacy/tf_privacy_compat.py`) -- the library's "
            "ecosystem currency for very recent TensorFlow releases is a real, practical risk for anyone "
            "reusing this code.",
            "",
            "## 10. Recommendations Before Module 5",
            "- Consider whether Module 5 (Fairness Analysis) should account for DP-SGD's documented "
            "interaction with class-imbalance handling -- a DP-trained model's fairness properties may "
            "differ from a normally-trained model's for reasons distinct from the sensitive attribute itself.",
            "- If a stronger privacy guarantee is required for production use, the noise multiplier sweep "
            "in Section 7 shows the achievable epsilon/utility tradeoff points actually measured on this "
            "dataset/architecture -- use it to pick an operating point rather than guessing.",
        ]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("DP report written to %s", output_path)
