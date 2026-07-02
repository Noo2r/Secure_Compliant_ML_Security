import numpy as np

from src.privacy.dp_experiment import DPExperimentResult, run_dp_experiment
from src.privacy.dp_model import DPNeuralNetworkTrainer

_ARCH = {"n_layers": 1, "units": 8, "dropout": 0.1, "learning_rate": 1e-3}


def _tiny_dataset(n: int = 256):
    rng = np.random.default_rng(0)
    X = rng.normal(size=(n, 5)).astype("float32")
    y = (X[:, 0] > 0).astype("float32")
    return X, y


def test_run_dp_experiment_returns_full_result_record() -> None:
    X_train, y_train = _tiny_dataset(256)
    X_val, y_val = _tiny_dataset(64)
    trainer = DPNeuralNetworkTrainer(architecture_params=_ARCH, class_weight_positive=1.0, random_state=42)

    result = run_dp_experiment(
        "test_experiment", trainer, X_train, y_train, X_val, y_val,
        batch_size=32, epochs=1, l2_norm_clip=1.0, noise_multiplier=1.1, microbatches=32, delta=1e-5,
    )
    assert isinstance(result, DPExperimentResult)
    assert result.experiment_name == "test_experiment"
    assert result.epsilon > 0
    assert 0 <= result.roc_auc <= 1
    assert 0 <= result.pr_auc <= 1
    assert result.confusion_matrix  # non-empty dict
    assert len(result.loss_history) == 1  # 1 epoch


def test_run_dp_experiment_evaluates_on_validation_not_training_data() -> None:
    """The experiment must threshold/evaluate on the passed-in validation
    set, not accidentally reuse training data -- verified by using disjoint,
    differently-distributed train/val sets and confirming the report reflects
    the validation set's actual positive rate characteristics.
    """
    X_train, y_train = _tiny_dataset(256)
    X_val = np.random.default_rng(1).normal(size=(100, 5)).astype("float32")
    y_val = np.zeros(100, dtype="float32")  # all-negative validation set
    trainer = DPNeuralNetworkTrainer(architecture_params=_ARCH, class_weight_positive=1.0, random_state=42)

    result = run_dp_experiment(
        "test_all_negative_val", trainer, X_train, y_train, X_val, y_val,
        batch_size=32, epochs=1, l2_norm_clip=1.0, noise_multiplier=1.1, microbatches=32, delta=1e-5,
    )
    # With an all-negative validation set, recall/precision/F1 for the
    # positive class are trivially 0 -- confirms the metrics were computed
    # against y_val, not some other label array.
    assert result.recall == 0.0
    assert result.confusion_matrix["true_positive"] == 0


def test_experiment_result_to_row_is_flat_and_dataframe_appendable() -> None:
    X_train, y_train = _tiny_dataset(256)
    X_val, y_val = _tiny_dataset(64)
    trainer = DPNeuralNetworkTrainer(architecture_params=_ARCH, class_weight_positive=1.0, random_state=42)
    result = run_dp_experiment(
        "test_row", trainer, X_train, y_train, X_val, y_val,
        batch_size=32, epochs=1, l2_norm_clip=1.0, noise_multiplier=1.1, microbatches=32, delta=1e-5,
    )
    row = result.to_row()
    assert isinstance(row["confusion_matrix"], str)  # dict serialized to string for CSV-friendliness
    assert isinstance(row["loss_history"], str)
    assert row["experiment_name"] == "test_row"


def test_different_l2_norm_clip_does_not_change_epsilon() -> None:
    """Direct experimental verification of the DP theory claim central to the
    investigation report: epsilon depends only on noise_multiplier (and
    num_examples/batch_size/epochs/delta), NOT on l2_norm_clip.
    """
    X_train, y_train = _tiny_dataset(256)
    X_val, y_val = _tiny_dataset(64)

    epsilons = []
    for clip in (0.5, 5.0, 50.0):
        trainer = DPNeuralNetworkTrainer(architecture_params=_ARCH, class_weight_positive=1.0, random_state=42)
        result = run_dp_experiment(
            f"clip_{clip}", trainer, X_train, y_train, X_val, y_val,
            batch_size=32, epochs=1, l2_norm_clip=clip, noise_multiplier=1.1, microbatches=32, delta=1e-5,
        )
        epsilons.append(result.epsilon)

    assert epsilons[0] == epsilons[1] == epsilons[2]
