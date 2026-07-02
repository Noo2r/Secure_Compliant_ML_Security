import numpy as np
import pandas as pd

from src.config.config_loader import (
    FairlearnValidationConfig,
    FairnessAnalysisConfig,
    FairnessPlotsConfig,
    FairnessStatisticsConfig,
    FairnessThresholdsConfig,
    ProtectedAttributeConfig,
)
from src.fairness.attribute_analysis import analyze_protected_attribute
from src.fairness.fairness_report_builder import FairnessReportBuilder

_STATS_CFG = FairnessStatisticsConfig(
    bootstrap_iterations=50, bootstrap_confidence_level=0.95, significance_alpha=0.05,
    min_expected_cell_count_for_chi_square=5.0, random_state=42,
)
_THRESHOLDS = FairnessThresholdsConfig(
    disparate_impact_low=0.8, disparate_impact_high=1.25,
    max_acceptable_spd=0.10, max_acceptable_eod=0.10, max_acceptable_aod=0.10,
)


def _build_one_result():
    rng = np.random.default_rng(0)
    n = 400
    y_true = rng.binomial(1, 0.1, size=n)
    y_pred = rng.binomial(1, 0.15, size=n)
    y_proba = rng.uniform(size=n)
    raw_groups = pd.Series(rng.choice(["debit", "credit"], size=n))
    attr_cfg = ProtectedAttributeConfig(name="card6", description="test attribute", reference_group="debit", primary=True)
    return analyze_protected_attribute(
        y_true, y_pred, y_proba, raw_groups, attr_cfg, _STATS_CFG, _THRESHOLDS,
        fairlearn_enabled=False, fairlearn_tolerance=1e-6,
    )


def _fairness_config(attr_cfg: ProtectedAttributeConfig) -> FairnessAnalysisConfig:
    return FairnessAnalysisConfig(
        primary_model="lightgbm", include_dp_model_comparison=False,
        protected_attributes=(attr_cfg,), fairness_thresholds=_THRESHOLDS, statistics=_STATS_CFG,
        fairlearn_validation=FairlearnValidationConfig(enabled=False, tolerance=1e-6),
        plots=FairnessPlotsConfig(dpi=80, top_n_features_shown=10),
    )


def test_fairness_report_md_is_generated_and_contains_key_sections(tmp_path) -> None:
    result = _build_one_result()
    attr_cfg = ProtectedAttributeConfig(name="card6", description="test", reference_group="debit", primary=True)
    FairnessReportBuilder().build("lightgbm", "test-version", [result], _fairness_config(attr_cfg), tmp_path)

    report_path = tmp_path / "fairness_report.md"
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "Executive Summary" in content
    assert "card6" in content
    assert "Proxy Limitations" in content
    assert "None of the attributes analyzed below are true demographic attributes" in content


def test_bias_findings_md_is_generated(tmp_path) -> None:
    result = _build_one_result()
    attr_cfg = ProtectedAttributeConfig(name="card6", description="test", reference_group="debit", primary=True)
    FairnessReportBuilder().build("lightgbm", "test-version", [result], _fairness_config(attr_cfg), tmp_path)

    findings_path = tmp_path / "bias_findings.md"
    assert findings_path.exists()
    content = findings_path.read_text(encoding="utf-8")
    assert "card6" in content


def test_report_handles_empty_results_list_without_crashing(tmp_path) -> None:
    attr_cfg = ProtectedAttributeConfig(name="card6", description="test", reference_group="debit", primary=True)
    FairnessReportBuilder().build("lightgbm", "test-version", [], _fairness_config(attr_cfg), tmp_path)
    assert (tmp_path / "fairness_report.md").exists()
    assert (tmp_path / "bias_findings.md").exists()
