import numpy as np

from src.privacy.dp_diagnostics import (
    GradientNormReport,
    compute_per_example_gradient_norms,
    run_gradient_norm_diagnostic,
    summarize_gradient_norms,
)
from src.models.keras_wrapper import KerasClassifierWrapper

_ARCH = {"n_layers": 1, "units": 8, "dropout": 0.1, "learning_rate": 1e-3}


def _tiny_imbalanced_dataset(n: int = 200):
    rng = np.random.default_rng(0)
    X = rng.normal(size=(n, 4)).astype("float32")
    y = np.zeros(n, dtype="float32")
    y[:20] = 1  # 10% positive, imbalanced like the real dataset
    rng.shuffle(y)
    return X, y


def test_compute_per_example_gradient_norms_returns_one_norm_per_example() -> None:
    X, y = _tiny_imbalanced_dataset()
    wrapper = KerasClassifierWrapper(**_ARCH, random_state=42)
    model = wrapper._build_model(X.shape[1])
    norms = compute_per_example_gradient_norms(model, X, y, class_weight={0: 1.0, 1: 1.0}, n_samples=50)
    assert len(norms) == 50
    assert (norms >= 0).all()


def test_higher_class_weight_increases_positive_example_gradient_norms() -> None:
    """Directly tests the mechanism the investigation's root-cause analysis
    depends on: class_weight scales the loss (and therefore the raw,
    pre-clip gradient) for the weighted class -- this must be true BEFORE
    trusting any conclusion about clipping neutralizing it.
    """
    X, y = _tiny_imbalanced_dataset()
    wrapper = KerasClassifierWrapper(**_ARCH, random_state=42)
    model = wrapper._build_model(X.shape[1])
    positive_idx = np.where(y == 1)[0]

    unweighted_norms = compute_per_example_gradient_norms(
        model, X[positive_idx], y[positive_idx], class_weight={0: 1.0, 1: 1.0}, n_samples=20
    )
    weighted_norms = compute_per_example_gradient_norms(
        model, X[positive_idx], y[positive_idx], class_weight={0: 1.0, 1: 20.0}, n_samples=20
    )
    assert np.mean(weighted_norms) > np.mean(unweighted_norms)


def test_summarize_gradient_norms_computes_expected_statistics() -> None:
    norms = np.array([0.1, 0.5, 1.0, 2.0, 5.0, 10.0])
    report = summarize_gradient_norms(norms, label="test", l2_norm_clip=1.0)
    assert isinstance(report, GradientNormReport)
    assert report.n_examples == 6
    assert report.median == 1.5
    assert report.max == 10.0
    # 3 of 6 values (2.0, 5.0, 10.0) exceed the clip norm of 1.0
    assert report.fraction_above_clip == 0.5


def test_run_gradient_norm_diagnostic_returns_positive_negative_and_all_reports() -> None:
    X, y = _tiny_imbalanced_dataset()
    wrapper = KerasClassifierWrapper(**_ARCH, random_state=42)
    model = wrapper._build_model(X.shape[1])
    reports = run_gradient_norm_diagnostic(model, X, y, class_weight={0: 1.0, 1: 10.0}, l2_norm_clip=1.0, n_samples=15)
    assert set(reports.keys()) == {"positive", "negative", "all"}
    assert reports["all"].n_examples == reports["positive"].n_examples + reports["negative"].n_examples
