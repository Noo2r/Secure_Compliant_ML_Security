from src.privacy.privacy_accountant import PrivacyAccountant, PrivacyBudget


def test_compute_returns_privacy_budget() -> None:
    accountant = PrivacyAccountant()
    budget = accountant.compute(num_examples=10_000, batch_size=250, noise_multiplier=1.1, epochs=5, delta=1e-5)
    assert isinstance(budget, PrivacyBudget)
    assert budget.epsilon > 0
    assert budget.epsilon_poisson_assumption > 0
    assert budget.delta == 1e-5
    assert "DP-SGD" in budget.statement


def test_no_subsampling_epsilon_is_more_conservative_than_poisson_assumption() -> None:
    """The epsilon that matches our actual (non-Poisson) training loop must be
    >= the optimistic Poisson-sampling epsilon -- if this ever flipped, we'd
    be under-reporting the real privacy cost.
    """
    accountant = PrivacyAccountant()
    budget = accountant.compute(num_examples=10_000, batch_size=250, noise_multiplier=1.1, epochs=5, delta=1e-5)
    assert budget.epsilon >= budget.epsilon_poisson_assumption


def test_higher_noise_multiplier_gives_smaller_epsilon() -> None:
    """More noise -> stronger privacy -> smaller epsilon (monotonicity check,
    not a hardcoded reference value, since the exact accounting math is
    TF-Privacy's responsibility, not this project's).
    """
    accountant = PrivacyAccountant()
    low_noise = accountant.compute(num_examples=10_000, batch_size=250, noise_multiplier=0.6, epochs=5, delta=1e-5)
    high_noise = accountant.compute(num_examples=10_000, batch_size=250, noise_multiplier=2.0, epochs=5, delta=1e-5)
    assert high_noise.epsilon < low_noise.epsilon


def test_more_epochs_gives_larger_epsilon() -> None:
    """More training steps at a fixed noise multiplier -> more cumulative
    privacy loss -> larger epsilon.
    """
    accountant = PrivacyAccountant()
    fewer_epochs = accountant.compute(num_examples=10_000, batch_size=250, noise_multiplier=1.1, epochs=2, delta=1e-5)
    more_epochs = accountant.compute(num_examples=10_000, batch_size=250, noise_multiplier=1.1, epochs=20, delta=1e-5)
    assert more_epochs.epsilon > fewer_epochs.epsilon


def test_privacy_budget_to_dict_round_trips_fields() -> None:
    accountant = PrivacyAccountant()
    budget = accountant.compute(num_examples=10_000, batch_size=250, noise_multiplier=1.1, epochs=5, delta=1e-5)
    d = budget.to_dict()
    assert d["epsilon"] == budget.epsilon
    assert d["noise_multiplier"] == 1.1
    assert d["num_examples"] == 10_000
