import mlflow
import numpy as np

from src.privacy.dp_mlflow import log_dp_variant_run
from src.privacy.dp_model import DPNeuralNetworkTrainer
from src.privacy.privacy_accountant import PrivacyAccountant
from src.evaluation.metrics import compute_classification_metrics
from src.tracking.mlflow_utils import MLflowTracker

_ARCH = {"n_layers": 1, "units": 8, "dropout": 0.1, "learning_rate": 1e-3}


def _tiny_dataset(n: int = 64):
    rng = np.random.default_rng(0)
    X = rng.normal(size=(n, 4)).astype("float32")
    y = (X[:, 0] > 0).astype("float32")
    return X, y


def test_log_dp_variant_run_creates_a_run_with_expected_tags_and_metrics(tmp_path) -> None:
    tracking_uri = f"sqlite:///{tmp_path / 'mlflow_test.db'}"
    tracker = MLflowTracker(tracking_uri=tracking_uri, experiment_name="dp-test-experiment")

    X, y = _tiny_dataset()
    trainer = DPNeuralNetworkTrainer(architecture_params=_ARCH, class_weight_positive=1.0, random_state=42)
    result = trainer.train_normal(X, y, batch_size=16, epochs=1)
    proba = result.model.predict(X, verbose=0).ravel()
    metrics = compute_classification_metrics(y, proba, threshold=0.5)

    with tracker.start_parent_run(run_name="dp_test_parent", dataset_version="test-v1"):
        run_id = log_dp_variant_run(
            "normal_nn", result, metrics, dataset_version="test-v1",
            architecture_params=_ARCH, batch_size=16, epochs=1,
        )

    client = mlflow.tracking.MlflowClient(tracking_uri=tracking_uri)
    run = client.get_run(run_id)
    assert run.info.status == "FINISHED"
    assert run.data.tags["variant"] == "normal_nn"
    assert run.data.tags["dataset_version"] == "test-v1"
    assert "pr_auc" in run.data.metrics
    assert run.data.params["batch_size"] == "16"


def test_log_dp_variant_run_logs_privacy_metrics_for_dp_variant(tmp_path) -> None:
    tracking_uri = f"sqlite:///{tmp_path / 'mlflow_test.db'}"
    tracker = MLflowTracker(tracking_uri=tracking_uri, experiment_name="dp-test-experiment-2")

    X, y = _tiny_dataset()
    trainer = DPNeuralNetworkTrainer(architecture_params=_ARCH, class_weight_positive=1.0, random_state=42)
    result = trainer.train_dp(
        X, y, batch_size=16, epochs=1, l2_norm_clip=1.0, noise_multiplier=1.1, microbatches=16,
    )
    budget = PrivacyAccountant().compute(num_examples=len(X), batch_size=16, noise_multiplier=1.1, epochs=1, delta=1e-5)
    proba = result.model.predict(X, verbose=0).ravel()
    metrics = compute_classification_metrics(y, proba, threshold=0.5)

    with tracker.start_parent_run(run_name="dp_test_parent2", dataset_version="test-v1"):
        run_id = log_dp_variant_run(
            "dp_nn", result, metrics, dataset_version="test-v1",
            architecture_params=_ARCH, batch_size=16, epochs=1,
            privacy_params={"l2_norm_clip": 1.0, "noise_multiplier": 1.1, "microbatches": 16},
            privacy_budget=budget,
        )

    client = mlflow.tracking.MlflowClient(tracking_uri=tracking_uri)
    run = client.get_run(run_id)
    assert run.data.metrics["epsilon"] == budget.epsilon
    assert run.data.params["dp_noise_multiplier"] == "1.1"
