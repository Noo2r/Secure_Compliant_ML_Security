import dataclasses

import pytest

from src.config.config_loader import DifferentialPrivacyConfig


def test_differential_privacy_config_loads_from_app_config(app_config) -> None:
    dp_cfg = app_config.differential_privacy
    assert dp_cfg.batch_size > 0
    assert dp_cfg.epochs > 0
    assert dp_cfg.l2_norm_clip > 0
    assert dp_cfg.noise_multiplier > 0
    assert dp_cfg.delta > 0
    assert len(dp_cfg.noise_multiplier_sweep) > 0


def test_microbatches_must_evenly_divide_batch_size() -> None:
    with pytest.raises(ValueError, match="evenly divide"):
        DifferentialPrivacyConfig(
            batch_size=256, epochs=11, l2_norm_clip=1.0, noise_multiplier=1.1,
            microbatches=100, delta=1e-5, noise_multiplier_sweep=(1.0,),
        )


def test_microbatches_equal_to_batch_size_is_valid() -> None:
    cfg = DifferentialPrivacyConfig(
        batch_size=256, epochs=11, l2_norm_clip=1.0, noise_multiplier=1.1,
        microbatches=256, delta=1e-5, noise_multiplier_sweep=(1.0,),
    )
    assert cfg.microbatches == 256


def test_paths_m4_are_absolute(app_config) -> None:
    assert app_config.paths_m4.artifacts_m4_dir.is_absolute()
    assert app_config.paths_m4.reports_m4_dir.is_absolute()
