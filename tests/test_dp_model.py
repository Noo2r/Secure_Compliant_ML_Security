import numpy as np
import pytest

from src.privacy.dp_model import DPNeuralNetworkTrainer, TrainingRunResult

_ARCH = {"n_layers": 1, "units": 8, "dropout": 0.1, "learning_rate": 1e-3}


def _tiny_dataset(n: int = 128):
    rng = np.random.default_rng(0)
    X = rng.normal(size=(n, 5)).astype("float32")
    y = (X[:, 0] > 0).astype("float32")
    return X, y


def test_train_normal_returns_training_run_result() -> None:
    X, y = _tiny_dataset()
    trainer = DPNeuralNetworkTrainer(architecture_params=_ARCH, class_weight_positive=1.0, random_state=42)
    result = trainer.train_normal(X, y, batch_size=32, epochs=2)
    assert isinstance(result, TrainingRunResult)
    assert result.variant == "normal"
    assert "loss" in result.history
    assert len(result.history["loss"]) == 2
    assert result.train_seconds > 0


def test_train_dp_returns_training_run_result() -> None:
    X, y = _tiny_dataset()
    trainer = DPNeuralNetworkTrainer(architecture_params=_ARCH, class_weight_positive=1.0, random_state=42)
    result = trainer.train_dp(
        X, y, batch_size=32, epochs=2, l2_norm_clip=1.0, noise_multiplier=1.1, microbatches=32,
    )
    assert result.variant == "dp"
    assert "loss" in result.history
    assert len(result.history["loss"]) == 2


def test_dp_training_requires_microbatches_to_divide_batch_size() -> None:
    X, y = _tiny_dataset()
    trainer = DPNeuralNetworkTrainer(architecture_params=_ARCH, class_weight_positive=1.0, random_state=42)
    with pytest.raises(ValueError, match="evenly divide"):
        trainer.train_dp(
            X, y, batch_size=32, epochs=1, l2_norm_clip=1.0, noise_multiplier=1.1, microbatches=5,
        )


def test_normal_and_dp_start_from_identical_initial_weights() -> None:
    """The core experimental-design property this module depends on: both
    variants must start from the same architecture AND the same initial
    weights, so any difference in trained behavior is attributable to the
    optimizer, not to a lucky/unlucky random initialization.
    """
    X, y = _tiny_dataset()
    trainer = DPNeuralNetworkTrainer(architecture_params=_ARCH, class_weight_positive=1.0, random_state=42)
    normal_result = trainer.train_normal(X, y, batch_size=32, epochs=1)
    dp_result = trainer.train_dp(
        X, y, batch_size=32, epochs=1, l2_norm_clip=1.0, noise_multiplier=1.1, microbatches=32,
    )
    assert normal_result.initial_weights_checksum == pytest.approx(dp_result.initial_weights_checksum, abs=1e-6)


def test_dp_training_applies_class_weight_without_crashing() -> None:
    X, y = _tiny_dataset()
    trainer = DPNeuralNetworkTrainer(architecture_params=_ARCH, class_weight_positive=25.0, random_state=42)
    result = trainer.train_dp(
        X, y, batch_size=32, epochs=1, l2_norm_clip=1.0, noise_multiplier=1.1, microbatches=32,
    )
    assert result.variant == "dp"


def test_ragged_final_batch_is_truncated_not_crashed() -> None:
    """Reproduces the real bug found running Module 4 on the full dataset:
    a dataset size not evenly divisible by batch_size produces a smaller
    final batch, which crashes DP per-example microbatching with an
    InvalidArgumentError. Both variants must silently truncate to a clean
    multiple of batch_size instead of crashing (or leaving the two variants
    trained on different-sized data).
    """
    rng = np.random.default_rng(0)
    n = 100  # not a multiple of batch_size=32 (100 // 32 * 32 = 96)
    X = rng.normal(size=(n, 5)).astype("float32")
    y = (X[:, 0] > 0).astype("float32")
    trainer = DPNeuralNetworkTrainer(architecture_params=_ARCH, class_weight_positive=1.0, random_state=42)

    dp_result = trainer.train_dp(
        X, y, batch_size=32, epochs=1, l2_norm_clip=1.0, noise_multiplier=1.1, microbatches=32,
    )
    assert dp_result.variant == "dp"  # must not raise

    truncated_X, truncated_y = trainer._truncate_to_batch_multiple(X, y, batch_size=32)
    assert len(truncated_X) == 96
    assert len(truncated_y) == 96


def test_truncate_to_batch_multiple_is_a_no_op_when_already_evenly_divisible() -> None:
    X, y = _tiny_dataset(n=128)  # 128 is a multiple of 32
    trainer = DPNeuralNetworkTrainer(architecture_params=_ARCH, class_weight_positive=1.0, random_state=42)
    truncated_X, truncated_y = trainer._truncate_to_batch_multiple(X, y, batch_size=32)
    assert len(truncated_X) == 128
    assert truncated_X is X  # returns the same array, no copy needed


def test_different_random_state_changes_initial_weights() -> None:
    """Sanity check that the checksum actually reflects the weights (not a
    constant), by confirming a different seed gives a different checksum.
    """
    X, y = _tiny_dataset()
    trainer_a = DPNeuralNetworkTrainer(architecture_params=_ARCH, class_weight_positive=1.0, random_state=1)
    trainer_b = DPNeuralNetworkTrainer(architecture_params=_ARCH, class_weight_positive=1.0, random_state=2)
    result_a = trainer_a.train_normal(X, y, batch_size=32, epochs=1)
    result_b = trainer_b.train_normal(X, y, batch_size=32, epochs=1)
    assert result_a.initial_weights_checksum != pytest.approx(result_b.initial_weights_checksum, abs=1e-9)
