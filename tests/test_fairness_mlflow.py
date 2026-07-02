import mlflow
import numpy as np
import pandas as pd

from src.config.config_loader import FairnessStatisticsConfig, FairnessThresholdsConfig, ProtectedAttributeConfig
from src.fairness.attribute_analysis import analyze_protected_attribute
from src.fairness.fairness_mlflow import FairnessMLflowLogger

_STATS_CFG = FairnessStatisticsConfig(
    bootstrap_iterations=50, bootstrap_confidence_level=0.95, significance_alpha=0.05,
    min_expected_cell_count_for_chi_square=5.0, random_state=42,
)
_THRESHOLDS = FairnessThresholdsConfig(
    disparate_impact_low=0.8, disparate_impact_high=1.25,
    max_acceptable_spd=0.10, max_acceptable_eod=0.10, max_acceptable_aod=0.10,
)


def _build_results():
    rng = np.random.default_rng(0)
    n = 300
    y_true = rng.binomial(1, 0.1, size=n)
    y_pred = rng.binomial(1, 0.15, size=n)
    y_proba = rng.uniform(size=n)
    raw_groups = pd.Series(rng.choice(["debit", "credit"], size=n))
    attr_cfg = ProtectedAttributeConfig(name="card6", description="test", reference_group="debit", primary=True)
    result = analyze_protected_attribute(
        y_true, y_pred, y_proba, raw_groups, attr_cfg, _STATS_CFG, _THRESHOLDS,
        fairlearn_enabled=False, fairlearn_tolerance=1e-6,
    )
    return [result]


def test_log_fairness_run_creates_run_with_expected_tags_and_metrics(tmp_path) -> None:
    tracking_uri = f"sqlite:///{tmp_path / 'fairness_mlflow_test.db'}"
    logger = FairnessMLflowLogger(tracking_uri=tracking_uri, experiment_name="fairness-test-experiment")

    results = _build_results()
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    (artifact_dir / "dummy.txt").write_text("test artifact")

    run_id = logger.log_fairness_run("lightgbm", "test-version", results, artifact_dir)

    client = mlflow.tracking.MlflowClient(tracking_uri=tracking_uri)
    run = client.get_run(run_id)
    assert run.info.status == "FINISHED"
    assert run.data.tags["model_name"] == "lightgbm"
    assert run.data.tags["dataset_version"] == "test-version"
    assert any(k.startswith("card6.") for k in run.data.metrics)


def test_log_fairness_run_handles_no_pairwise_metrics_gracefully(tmp_path) -> None:
    tracking_uri = f"sqlite:///{tmp_path / 'fairness_mlflow_test2.db'}"
    logger = FairnessMLflowLogger(tracking_uri=tracking_uri, experiment_name="fairness-test-experiment-2")

    rng = np.random.default_rng(1)
    n = 100
    y_true = rng.binomial(1, 0.1, size=n)
    y_pred = rng.binomial(1, 0.1, size=n)
    y_proba = rng.uniform(size=n)
    raw_groups = pd.Series(["only_group"] * n)
    attr_cfg = ProtectedAttributeConfig(name="test_attr", description="test", reference_group="does_not_exist", primary=True)
    result = analyze_protected_attribute(
        y_true, y_pred, y_proba, raw_groups, attr_cfg, _STATS_CFG, _THRESHOLDS,
        fairlearn_enabled=False, fairlearn_tolerance=1e-6,
    )
    artifact_dir = tmp_path / "artifacts2"
    artifact_dir.mkdir()
    run_id = logger.log_fairness_run("lightgbm", "test-version", [result], artifact_dir)
    client = mlflow.tracking.MlflowClient(tracking_uri=tracking_uri)
    assert client.get_run(run_id).info.status == "FINISHED"
