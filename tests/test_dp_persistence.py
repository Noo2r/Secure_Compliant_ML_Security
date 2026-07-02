import numpy as np

from src.privacy.dp_model import DPNeuralNetworkTrainer
from src.privacy.dp_persistence import DPModelArtifact, DPModelMetadata
from src.privacy.privacy_accountant import PrivacyAccountant

_ARCH = {"n_layers": 1, "units": 8, "dropout": 0.1, "learning_rate": 1e-3}


def _tiny_dataset(n: int = 64):
    rng = np.random.default_rng(0)
    X = rng.normal(size=(n, 4)).astype("float32")
    y = (X[:, 0] > 0).astype("float32")
    return X, y


def test_save_and_load_normal_model_round_trips(tmp_path) -> None:
    X, y = _tiny_dataset()
    trainer = DPNeuralNetworkTrainer(architecture_params=_ARCH, class_weight_positive=1.0, random_state=42)
    result = trainer.train_normal(X, y, batch_size=16, epochs=1)

    output_dir = tmp_path / "normal_nn"
    metadata = DPModelArtifact.save(
        model=result.model, variant="normal", dataset_version="test-v1",
        architecture_params=_ARCH, batch_size=16, epochs=1,
        train_seconds=result.train_seconds, random_state=42, output_dir=output_dir,
    )
    assert (output_dir / "model.keras").exists()
    assert (output_dir / "metadata.json").exists()
    assert metadata.variant == "normal"
    assert metadata.privacy_params is None
    assert metadata.privacy_budget is None

    loaded_model, loaded_metadata = DPModelArtifact.load(output_dir)
    original_proba = result.model.predict(X, verbose=0)
    reloaded_proba = loaded_model.predict(X, verbose=0)
    np.testing.assert_allclose(original_proba, reloaded_proba, atol=1e-5)
    assert loaded_metadata.dataset_version == "test-v1"
    assert loaded_metadata.batch_size == 16


def test_save_and_load_dp_model_includes_privacy_metadata(tmp_path) -> None:
    X, y = _tiny_dataset()
    trainer = DPNeuralNetworkTrainer(architecture_params=_ARCH, class_weight_positive=1.0, random_state=42)
    result = trainer.train_dp(
        X, y, batch_size=16, epochs=1, l2_norm_clip=1.0, noise_multiplier=1.1, microbatches=16,
    )
    budget = PrivacyAccountant().compute(
        num_examples=len(X), batch_size=16, noise_multiplier=1.1, epochs=1, delta=1e-5
    )
    output_dir = tmp_path / "dp_nn"
    metadata = DPModelArtifact.save(
        model=result.model, variant="dp", dataset_version="test-v1",
        architecture_params=_ARCH, batch_size=16, epochs=1,
        train_seconds=result.train_seconds, random_state=42, output_dir=output_dir,
        privacy_params={"l2_norm_clip": 1.0, "noise_multiplier": 1.1, "microbatches": 16},
        privacy_budget=budget,
    )
    assert metadata.variant == "dp"
    assert metadata.privacy_params == {"l2_norm_clip": 1.0, "noise_multiplier": 1.1, "microbatches": 16}
    assert metadata.privacy_budget["epsilon"] == budget.epsilon

    _, loaded_metadata = DPModelArtifact.load(output_dir)
    assert loaded_metadata.privacy_budget["epsilon"] == budget.epsilon


def test_metadata_json_is_plain_text_readable_without_loading_keras(tmp_path) -> None:
    """The metadata sidecar must be readable without importing TensorFlow at
    all -- a quick-audit requirement, not just a persistence nicety.
    """
    import json

    X, y = _tiny_dataset()
    trainer = DPNeuralNetworkTrainer(architecture_params=_ARCH, class_weight_positive=1.0, random_state=42)
    result = trainer.train_normal(X, y, batch_size=16, epochs=1)
    output_dir = tmp_path / "normal_nn"
    DPModelArtifact.save(
        model=result.model, variant="normal", dataset_version="test-v1",
        architecture_params=_ARCH, batch_size=16, epochs=1,
        train_seconds=result.train_seconds, random_state=42, output_dir=output_dir,
    )
    with open(output_dir / "metadata.json", "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    assert raw["variant"] == "normal"
    assert raw["architecture_params"] == _ARCH
