import numpy as np
import pandas as pd

from src.privacy.dp_evaluation import evaluate_and_compare
from src.privacy.dp_model import TrainingRunResult
from src.privacy.dp_report_builder import DPReportBuilder
from src.privacy.privacy_accountant import PrivacyBudget

_ARCH = {"n_layers": 1, "units": 64, "dropout": 0.257, "learning_rate": 0.00153}


def _fake_training_result(variant: str) -> TrainingRunResult:
    return TrainingRunResult(
        variant=variant, model=None, history={"loss": [0.5, 0.4, 0.3], "pr_auc": [0.1, 0.15, 0.2]},
        train_seconds=12.3, initial_weights_checksum=1.2345,
    )


def _fake_comparison():
    rng = np.random.default_rng(0)
    n = 500
    y = rng.binomial(1, 0.2, size=n)
    normal_proba = np.clip(y * 0.6 + rng.normal(0, 0.15, size=n) + 0.15, 0, 1)
    dp_proba = np.clip(y * 0.2 + rng.normal(0, 0.3, size=n) + 0.15, 0, 1)
    budget = PrivacyBudget(
        epsilon=3.5, epsilon_poisson_assumption=1.2, delta=1e-5, noise_multiplier=1.1,
        num_examples=10_000, batch_size=256, epochs=11, statement="DP-SGD statement text",
    )
    return evaluate_and_compare(
        y_val=y, normal_proba_val=normal_proba, dp_proba_val=dp_proba,
        y_test=y, normal_proba_test=normal_proba, dp_proba_test=dp_proba,
        privacy_budget=budget, l2_norm_clip=1.0,
    ), budget


def test_dp_report_builder_writes_markdown_with_expected_sections(tmp_path) -> None:
    comparison, budget = _fake_comparison()
    sweep_df = pd.DataFrame({
        "noise_multiplier": [0.6, 1.1, 2.0],
        "epsilon": [10.0, 3.5, 0.9],
        "pr_auc": [0.25, 0.18, 0.05],
        "roc_auc": [0.75, 0.7, 0.6],
    })

    output_path = tmp_path / "dp_report.md"
    DPReportBuilder().build(
        architecture_params=_ARCH, batch_size=256, epochs=11,
        l2_norm_clip=1.0, noise_multiplier=1.1, microbatches=256,
        privacy_budget=budget,
        normal_result=_fake_training_result("normal"),
        dp_result=_fake_training_result("dp"),
        comparison=comparison, sweep_df=sweep_df, dataset_version="test-v1",
        output_path=output_path,
    )

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    for expected_section in [
        "## 1. Architecture", "## 2. Optimizer", "## 3. Differential Privacy Parameters",
        "## 4. Privacy Accounting", "## 5. Training Time", "## 6. Evaluation Metrics",
        "## 7. Privacy-Utility Analysis", "## 8. Advantages", "## 9. Limitations",
        "## 10. Recommendations",
    ]:
        assert expected_section in content
    assert "test-v1" in content
    assert "3.5" in content  # epsilon appears somewhere


def test_dp_report_includes_actual_metric_values(tmp_path) -> None:
    comparison, budget = _fake_comparison()
    sweep_df = pd.DataFrame({"noise_multiplier": [1.1], "epsilon": [3.5], "pr_auc": [0.18], "roc_auc": [0.7]})

    output_path = tmp_path / "dp_report.md"
    DPReportBuilder().build(
        architecture_params=_ARCH, batch_size=256, epochs=11,
        l2_norm_clip=1.0, noise_multiplier=1.1, microbatches=256,
        privacy_budget=budget,
        normal_result=_fake_training_result("normal"),
        dp_result=_fake_training_result("dp"),
        comparison=comparison, sweep_df=sweep_df, dataset_version="test-v1",
        output_path=output_path,
    )
    content = output_path.read_text(encoding="utf-8")
    assert f"{comparison.normal_metrics.pr_auc:.4f}" in content
    assert f"{comparison.dp_metrics.pr_auc:.4f}" in content
