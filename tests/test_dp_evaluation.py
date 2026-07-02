import numpy as np
import pytest

from src.privacy.dp_evaluation import DPComparisonResult, evaluate_and_compare
from src.privacy.privacy_accountant import PrivacyBudget


def _fake_budget() -> PrivacyBudget:
    return PrivacyBudget(
        epsilon=3.5, epsilon_poisson_assumption=1.2, delta=1e-5, noise_multiplier=1.1,
        num_examples=10_000, batch_size=256, epochs=11, statement="DP-SGD statement text",
    )


@pytest.fixture()
def synthetic_predictions():
    rng = np.random.default_rng(0)
    n = 1000
    y_val = rng.binomial(1, 0.2, size=n)
    y_test = rng.binomial(1, 0.2, size=n)
    # Normal model: cleanly separable signal.
    normal_val = np.clip(y_val * 0.7 + rng.normal(0, 0.1, size=n) + 0.15, 0, 1)
    normal_test = np.clip(y_test * 0.7 + rng.normal(0, 0.1, size=n) + 0.15, 0, 1)
    # DP model: same signal but heavily noised -> weaker separation.
    dp_val = np.clip(y_val * 0.2 + rng.normal(0, 0.3, size=n) + 0.15, 0, 1)
    dp_test = np.clip(y_test * 0.2 + rng.normal(0, 0.3, size=n) + 0.15, 0, 1)
    return y_val, normal_val, dp_val, y_test, normal_test, dp_test


def test_evaluate_and_compare_returns_result(synthetic_predictions) -> None:
    y_val, normal_val, dp_val, y_test, normal_test, dp_test = synthetic_predictions
    result = evaluate_and_compare(
        y_val=y_val, normal_proba_val=normal_val, dp_proba_val=dp_val,
        y_test=y_test, normal_proba_test=normal_test, dp_proba_test=dp_test,
        privacy_budget=_fake_budget(), l2_norm_clip=1.0,
    )
    assert isinstance(result, DPComparisonResult)
    assert 0 <= result.normal_metrics.pr_auc <= 1
    assert 0 <= result.dp_metrics.pr_auc <= 1


def test_noisier_dp_model_scores_lower_than_normal_model(synthetic_predictions) -> None:
    y_val, normal_val, dp_val, y_test, normal_test, dp_test = synthetic_predictions
    result = evaluate_and_compare(
        y_val=y_val, normal_proba_val=normal_val, dp_proba_val=dp_val,
        y_test=y_test, normal_proba_test=normal_test, dp_proba_test=dp_test,
        privacy_budget=_fake_budget(), l2_norm_clip=1.0,
    )
    # By construction, the DP predictions carry much weaker signal.
    assert result.normal_metrics.pr_auc > result.dp_metrics.pr_auc
    assert result.metric_deltas["pr_auc"] > 0


def test_explanation_references_actual_epsilon_and_noise_multiplier(synthetic_predictions) -> None:
    y_val, normal_val, dp_val, y_test, normal_test, dp_test = synthetic_predictions
    budget = _fake_budget()
    result = evaluate_and_compare(
        y_val=y_val, normal_proba_val=normal_val, dp_proba_val=dp_val,
        y_test=y_test, normal_proba_test=normal_test, dp_proba_test=dp_test,
        privacy_budget=budget, l2_norm_clip=1.0,
    )
    assert f"{budget.epsilon:.3f}" in result.explanation
    assert str(budget.noise_multiplier) in result.explanation


def test_thresholds_are_calibrated_independently_per_model(synthetic_predictions) -> None:
    y_val, normal_val, dp_val, y_test, normal_test, dp_test = synthetic_predictions
    result = evaluate_and_compare(
        y_val=y_val, normal_proba_val=normal_val, dp_proba_val=dp_val,
        y_test=y_test, normal_proba_test=normal_test, dp_proba_test=dp_test,
        privacy_budget=_fake_budget(), l2_norm_clip=1.0,
    )
    # Different underlying score distributions -> generally different optimal thresholds.
    assert result.normal_threshold.threshold != result.dp_threshold.threshold
