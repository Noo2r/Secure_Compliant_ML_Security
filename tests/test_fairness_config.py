from src.config.config_loader import AppConfig, FairnessAnalysisConfig


def test_fairness_analysis_config_loads(app_config: AppConfig) -> None:
    assert isinstance(app_config.fairness_analysis, FairnessAnalysisConfig)


def test_fairness_analysis_has_three_protected_attributes(app_config: AppConfig) -> None:
    names = [a.name for a in app_config.fairness_analysis.protected_attributes]
    assert names == ["card6", "card4", "DeviceType"]


def test_primary_attribute_is_card6(app_config: AppConfig) -> None:
    primary = app_config.fairness_analysis.primary_attribute()
    assert primary.name == "card6"
    assert primary.reference_group == "debit"


def test_device_type_excluded_from_primary_analysis(app_config: AppConfig) -> None:
    device_type = next(a for a in app_config.fairness_analysis.protected_attributes if a.name == "DeviceType")
    assert device_type.excluded_from_primary_analysis is True
    assert device_type.primary is False


def test_primary_model_is_lightgbm(app_config: AppConfig) -> None:
    assert app_config.fairness_analysis.primary_model == "lightgbm"


def test_dp_model_comparison_is_optional_not_primary(app_config: AppConfig) -> None:
    assert app_config.fairness_analysis.include_dp_model_comparison is True
    assert app_config.fairness_analysis.primary_model != "dp_nn"


def test_fairness_thresholds_four_fifths_rule(app_config: AppConfig) -> None:
    t = app_config.fairness_analysis.fairness_thresholds
    assert t.disparate_impact_low == 0.8
    assert t.disparate_impact_high == 1.25


def test_paths_m5_are_absolute(app_config: AppConfig) -> None:
    assert app_config.paths_m5.artifacts_m5_dir.is_absolute()
    assert app_config.paths_m5.reports_m5_dir.is_absolute()
