from pathlib import Path

from src.config.config_loader import AppConfig


def test_load_config_returns_app_config(app_config: AppConfig) -> None:
    assert isinstance(app_config, AppConfig)


def test_secure_data_mode_is_valid(app_config: AppConfig) -> None:
    assert app_config.secure_data.mode in {"load_existing", "regenerate"}


def test_paths_are_absolute_and_rooted_at_repo(app_config: AppConfig) -> None:
    assert app_config.paths.raw_transaction_csv.is_absolute()
    assert str(app_config.paths.raw_transaction_csv).startswith(str(app_config.repo_root))


def test_azure_ml_not_configured_without_env_vars(app_config: AppConfig) -> None:
    # In a local/dev environment with no Azure env vars exported, the
    # placeholders resolve to empty strings and is_configured must be False
    # so downstream code never attempts a live SDK call unintentionally.
    if not app_config.azure_ml.subscription_id:
        assert app_config.azure_ml.is_configured is False
