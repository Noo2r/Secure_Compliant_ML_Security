"""Typed configuration loader for Milestone 2.

Loads ``config.yaml`` into immutable, type-hinted dataclasses so that every
downstream module (data loading, training, fairness, explainability, risk
analysis, MLflow, Azure ML) reads configuration through a single validated
object instead of ad-hoc dict lookups scattered across the codebase.

Environment-variable placeholders in the YAML (``${VAR_NAME}``) are resolved
at load time, which keeps secrets and environment-specific values (Azure ML
subscription/workspace) out of version control while still being fully
config-driven.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")

# Repository root = two levels up from this file (src/config/config_loader.py -> repo root)
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


def _resolve_env_vars(value: Any) -> Any:
    """Recursively substitute ``${VAR_NAME}`` placeholders with environment values.

    Unresolved placeholders (env var not set) are left as an empty string
    rather than raising, since Azure ML credentials are legitimately absent
    in local/dev environments and should not block non-Azure modules.
    """
    if isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_vars(v) for v in value]
    if isinstance(value, str):
        def _sub(match: "re.Match[str]") -> str:
            return os.environ.get(match.group(1), "")
        return _ENV_VAR_PATTERN.sub(_sub, value)
    return value


@dataclass(frozen=True)
class PathsConfig:
    raw_transaction_csv: Path
    raw_identity_csv: Path
    encrypted_dataset_csv: Path
    encryption_key_file: Path
    processed_dir: Path
    reports_dir: Path
    reports_m2_dir: Path
    logs_dir: Path
    dataset_manifest_json: Path
    processed_train_csv: Path
    processed_test_csv: Path
    feature_manifest_json: Path
    artifacts_m2_dir: Path


@dataclass(frozen=True)
class UpstreamMilestone1Config:
    data_classification_csv: Path
    data_lineage_csv: Path
    access_control_csv: Path
    key_management_csv: Path
    dpia_report_csv: Path
    expected_columns_dropped: int
    missing_value_drop_threshold_pct: float


@dataclass(frozen=True)
class SecureDataConfig:
    mode: str  # "load_existing" | "regenerate"
    faker_seed: int
    merge_key: str
    target_column: str


@dataclass(frozen=True)
class ValidationConfig:
    max_allowed_duplicate_rows: int
    max_column_missing_pct_warning: float
    required_dtypes: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class FeatureEngineeringConfig:
    email_domain_top_n: int
    missing_indicator_min_missing_pct: float
    card_velocity_group_col: str


@dataclass(frozen=True)
class FeatureSelectionConfig:
    near_zero_variance_freq_threshold: float
    correlation_redundancy_threshold: float
    ranking_sample_size: int
    top_k_final_features: int


@dataclass(frozen=True)
class TrainTestSplitConfig:
    strategy: str  # "time_aware" | "stratified_random"
    test_size: float


@dataclass(frozen=True)
class FairnessConfig:
    primary_sensitive_attribute: str
    secondary_sensitive_attribute: str
    excluded_candidate_attribute: str


@dataclass(frozen=True)
class MetadataConfig:
    preserved_columns: tuple[str, ...]


@dataclass(frozen=True)
class LoggingConfig:
    level: str
    file_name: str
    max_bytes: int
    backup_count: int


@dataclass(frozen=True)
class AzureMLConfig:
    subscription_id: str
    resource_group: str
    workspace_name: str
    model_registry_name: str

    @property
    def is_configured(self) -> bool:
        """True only when all three Azure identifiers are non-empty.

        Downstream modules use this flag to decide whether to actually call
        the Azure ML SDK or to skip live registration and only emit the
        ready-to-run artifacts (see src/registry/azure_ml_registry.py).
        """
        return bool(self.subscription_id and self.resource_group and self.workspace_name)


@dataclass(frozen=True)
class MLflowConfig:
    tracking_uri: str
    experiment_name: str


@dataclass(frozen=True)
class ModelDevelopmentConfig:
    candidate_models: tuple[str, ...]
    cv_folds: int
    tuning_sample_size: int
    optuna_trials: dict[str, int]
    optuna_timeout_seconds: int
    primary_metric: str
    tie_break_relative_tolerance: float
    learning_curve_train_sizes: tuple[float, ...]
    validation_curve_points: int


@dataclass(frozen=True)
class OperationalMetricsConfig:
    precision_threshold: float
    top_k_values: tuple[int, ...]


@dataclass(frozen=True)
class ThresholdOptimizationConfig:
    strategy: str  # "max_f1" | "recall_at_precision"
    min_precision: float
    validation_fraction_of_train: float


@dataclass(frozen=True)
class PathsM3Config:
    artifacts_m3_dir: Path
    reports_m3_dir: Path


@dataclass(frozen=True)
class DifferentialPrivacyConfig:
    batch_size: int
    epochs: int
    l2_norm_clip: float
    noise_multiplier: float
    microbatches: int
    delta: float
    noise_multiplier_sweep: tuple[float, ...]

    def __post_init__(self) -> None:
        if self.batch_size % self.microbatches != 0:
            raise ValueError(
                f"differential_privacy.microbatches ({self.microbatches}) must evenly divide "
                f"batch_size ({self.batch_size})"
            )


@dataclass(frozen=True)
class PathsM4Config:
    artifacts_m4_dir: Path
    reports_m4_dir: Path


@dataclass(frozen=True)
class ProtectedAttributeConfig:
    name: str
    description: str
    reference_group: str
    primary: bool
    excluded_from_primary_analysis: bool = False


@dataclass(frozen=True)
class FairnessThresholdsConfig:
    disparate_impact_low: float
    disparate_impact_high: float
    max_acceptable_spd: float
    max_acceptable_eod: float
    max_acceptable_aod: float


@dataclass(frozen=True)
class FairnessStatisticsConfig:
    bootstrap_iterations: int
    bootstrap_confidence_level: float
    significance_alpha: float
    min_expected_cell_count_for_chi_square: float
    random_state: int


@dataclass(frozen=True)
class FairlearnValidationConfig:
    enabled: bool
    tolerance: float


@dataclass(frozen=True)
class FairnessPlotsConfig:
    dpi: int
    top_n_features_shown: int


@dataclass(frozen=True)
class FairnessAnalysisConfig:
    primary_model: str
    include_dp_model_comparison: bool
    protected_attributes: tuple[ProtectedAttributeConfig, ...]
    fairness_thresholds: FairnessThresholdsConfig
    statistics: FairnessStatisticsConfig
    fairlearn_validation: FairlearnValidationConfig
    plots: FairnessPlotsConfig

    def primary_attribute(self) -> ProtectedAttributeConfig:
        return next(a for a in self.protected_attributes if a.primary)


@dataclass(frozen=True)
class PathsM5Config:
    artifacts_m5_dir: Path
    reports_m5_dir: Path


@dataclass(frozen=True)
class ProjectConfig:
    name: str
    milestone: str
    owner: str
    random_seed: int


@dataclass(frozen=True)
class AppConfig:
    """Root configuration object composed of all sub-sections."""

    project: ProjectConfig
    paths: PathsConfig
    upstream_milestone1: UpstreamMilestone1Config
    secure_data: SecureDataConfig
    validation: ValidationConfig
    feature_engineering: FeatureEngineeringConfig
    feature_selection: FeatureSelectionConfig
    train_test_split: TrainTestSplitConfig
    fairness: FairnessConfig
    metadata: MetadataConfig
    logging: LoggingConfig
    azure_ml: AzureMLConfig
    mlflow: MLflowConfig
    model_development: ModelDevelopmentConfig
    operational_metrics: OperationalMetricsConfig
    threshold_optimization: ThresholdOptimizationConfig
    paths_m3: PathsM3Config
    differential_privacy: DifferentialPrivacyConfig
    paths_m4: PathsM4Config
    fairness_analysis: FairnessAnalysisConfig
    paths_m5: PathsM5Config
    repo_root: Path


def _to_abs_path(repo_root: Path, relative: str) -> Path:
    return (repo_root / relative).resolve()


def load_config(config_path: Path | str | None = None) -> AppConfig:
    """Load, resolve, and type-check ``config.yaml`` into an :class:`AppConfig`.

    Parameters
    ----------
    config_path:
        Optional override path to a YAML config file. Defaults to
        ``src/config/config.yaml`` inside the repository.

    Returns
    -------
    AppConfig
        Fully resolved, immutable configuration object. All relative paths
        are converted to absolute paths rooted at the repository root so
        that behaviour is identical regardless of the caller's working
        directory (a common source of bugs in notebook-driven pipelines).
    """
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    raw = _resolve_env_vars(raw)
    repo_root = REPO_ROOT

    paths = PathsConfig(
        raw_transaction_csv=_to_abs_path(repo_root, raw["paths"]["raw_transaction_csv"]),
        raw_identity_csv=_to_abs_path(repo_root, raw["paths"]["raw_identity_csv"]),
        encrypted_dataset_csv=_to_abs_path(repo_root, raw["paths"]["encrypted_dataset_csv"]),
        encryption_key_file=_to_abs_path(repo_root, raw["paths"]["encryption_key_file"]),
        processed_dir=_to_abs_path(repo_root, raw["paths"]["processed_dir"]),
        reports_dir=_to_abs_path(repo_root, raw["paths"]["reports_dir"]),
        reports_m2_dir=_to_abs_path(repo_root, raw["paths"]["reports_m2_dir"]),
        logs_dir=_to_abs_path(repo_root, raw["paths"]["logs_dir"]),
        dataset_manifest_json=_to_abs_path(repo_root, raw["paths"]["dataset_manifest_json"]),
        processed_train_csv=_to_abs_path(repo_root, raw["paths"]["processed_train_csv"]),
        processed_test_csv=_to_abs_path(repo_root, raw["paths"]["processed_test_csv"]),
        feature_manifest_json=_to_abs_path(repo_root, raw["paths"]["feature_manifest_json"]),
        artifacts_m2_dir=_to_abs_path(repo_root, raw["paths"]["artifacts_m2_dir"]),
    )

    upstream = raw["upstream_milestone1"]
    upstream_cfg = UpstreamMilestone1Config(
        data_classification_csv=_to_abs_path(repo_root, upstream["data_classification_csv"]),
        data_lineage_csv=_to_abs_path(repo_root, upstream["data_lineage_csv"]),
        access_control_csv=_to_abs_path(repo_root, upstream["access_control_csv"]),
        key_management_csv=_to_abs_path(repo_root, upstream["key_management_csv"]),
        dpia_report_csv=_to_abs_path(repo_root, upstream["dpia_report_csv"]),
        expected_columns_dropped=int(upstream["expected_columns_dropped"]),
        missing_value_drop_threshold_pct=float(upstream["missing_value_drop_threshold_pct"]),
    )

    secure_data_cfg = SecureDataConfig(**raw["secure_data"])
    validation_cfg = ValidationConfig(**raw["validation"])
    feature_engineering_cfg = FeatureEngineeringConfig(**raw["feature_engineering"])
    feature_selection_cfg = FeatureSelectionConfig(**raw["feature_selection"])
    train_test_split_cfg = TrainTestSplitConfig(**raw["train_test_split"])
    fairness_cfg = FairnessConfig(**raw["fairness"])
    metadata_cfg = MetadataConfig(preserved_columns=tuple(raw["metadata"]["preserved_columns"]))
    logging_cfg = LoggingConfig(**raw["logging"])
    azure_ml_cfg = AzureMLConfig(**raw["azure_ml"])
    mlflow_cfg = MLflowConfig(**raw["mlflow"])
    project_cfg = ProjectConfig(**raw["project"])

    model_dev_raw = raw["model_development"]
    model_development_cfg = ModelDevelopmentConfig(
        candidate_models=tuple(model_dev_raw["candidate_models"]),
        cv_folds=int(model_dev_raw["cv_folds"]),
        tuning_sample_size=int(model_dev_raw["tuning_sample_size"]),
        optuna_trials=dict(model_dev_raw["optuna_trials"]),
        optuna_timeout_seconds=int(model_dev_raw["optuna_timeout_seconds"]),
        primary_metric=model_dev_raw["primary_metric"],
        tie_break_relative_tolerance=float(model_dev_raw["tie_break_relative_tolerance"]),
        learning_curve_train_sizes=tuple(model_dev_raw["learning_curve_train_sizes"]),
        validation_curve_points=int(model_dev_raw["validation_curve_points"]),
    )
    operational_metrics_cfg = OperationalMetricsConfig(
        precision_threshold=float(raw["operational_metrics"]["precision_threshold"]),
        top_k_values=tuple(raw["operational_metrics"]["top_k_values"]),
    )
    threshold_optimization_cfg = ThresholdOptimizationConfig(**raw["threshold_optimization"])
    paths_m3_raw = raw["paths_m3"]
    paths_m3_cfg = PathsM3Config(
        artifacts_m3_dir=_to_abs_path(repo_root, paths_m3_raw["artifacts_m3_dir"]),
        reports_m3_dir=_to_abs_path(repo_root, paths_m3_raw["reports_m3_dir"]),
    )

    dp_raw = raw["differential_privacy"]
    differential_privacy_cfg = DifferentialPrivacyConfig(
        batch_size=int(dp_raw["batch_size"]),
        epochs=int(dp_raw["epochs"]),
        l2_norm_clip=float(dp_raw["l2_norm_clip"]),
        noise_multiplier=float(dp_raw["noise_multiplier"]),
        microbatches=int(dp_raw["microbatches"]),
        delta=float(dp_raw["delta"]),
        noise_multiplier_sweep=tuple(float(v) for v in dp_raw["noise_multiplier_sweep"]),
    )
    paths_m4_raw = raw["paths_m4"]
    paths_m4_cfg = PathsM4Config(
        artifacts_m4_dir=_to_abs_path(repo_root, paths_m4_raw["artifacts_m4_dir"]),
        reports_m4_dir=_to_abs_path(repo_root, paths_m4_raw["reports_m4_dir"]),
    )

    fairness_raw = raw["fairness_analysis"]
    protected_attributes_cfg = tuple(
        ProtectedAttributeConfig(
            name=a["name"],
            description=a["description"],
            reference_group=a["reference_group"],
            primary=bool(a["primary"]),
            excluded_from_primary_analysis=bool(a.get("excluded_from_primary_analysis", False)),
        )
        for a in fairness_raw["protected_attributes"]
    )
    fairness_analysis_cfg = FairnessAnalysisConfig(
        primary_model=fairness_raw["primary_model"],
        include_dp_model_comparison=bool(fairness_raw["include_dp_model_comparison"]),
        protected_attributes=protected_attributes_cfg,
        fairness_thresholds=FairnessThresholdsConfig(**fairness_raw["fairness_thresholds"]),
        statistics=FairnessStatisticsConfig(**fairness_raw["statistics"]),
        fairlearn_validation=FairlearnValidationConfig(**fairness_raw["fairlearn_validation"]),
        plots=FairnessPlotsConfig(**fairness_raw["plots"]),
    )
    paths_m5_raw = raw["paths_m5"]
    paths_m5_cfg = PathsM5Config(
        artifacts_m5_dir=_to_abs_path(repo_root, paths_m5_raw["artifacts_m5_dir"]),
        reports_m5_dir=_to_abs_path(repo_root, paths_m5_raw["reports_m5_dir"]),
    )

    if secure_data_cfg.mode not in {"load_existing", "regenerate"}:
        raise ValueError(
            f"secure_data.mode must be 'load_existing' or 'regenerate', got '{secure_data_cfg.mode}'"
        )

    return AppConfig(
        project=project_cfg,
        paths=paths,
        upstream_milestone1=upstream_cfg,
        secure_data=secure_data_cfg,
        validation=validation_cfg,
        feature_engineering=feature_engineering_cfg,
        feature_selection=feature_selection_cfg,
        train_test_split=train_test_split_cfg,
        fairness=fairness_cfg,
        metadata=metadata_cfg,
        logging=logging_cfg,
        azure_ml=azure_ml_cfg,
        mlflow=mlflow_cfg,
        model_development=model_development_cfg,
        operational_metrics=operational_metrics_cfg,
        threshold_optimization=threshold_optimization_cfg,
        paths_m3=paths_m3_cfg,
        differential_privacy=differential_privacy_cfg,
        paths_m4=paths_m4_cfg,
        fairness_analysis=fairness_analysis_cfg,
        paths_m5=paths_m5_cfg,
        repo_root=repo_root,
    )
