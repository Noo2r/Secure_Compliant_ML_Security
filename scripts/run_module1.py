"""Module 1 entrypoint: Data Loading, Validation & Integration.

Run from the repository root:

    python scripts/run_module1.py

This orchestrates, in order:
    1. Load configuration (src/config/config.yaml).
    2. Build the classification registry from Yara's Milestone 1 reports.
    3. Load/regenerate the secured dataset.
    4. Validate + verify the dataset.
    5. Persist the dataset manifest and validation report to reports_m2/.

Exits with status code 1 if any critical validation check fails, so this
script is CI/pipeline friendly (e.g. as a gate before Module 2 runs).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as `python scripts/run_module1.py` from the repo root without
# installing the project as a package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.config_loader import load_config
from src.data.classification_registry import DataClassificationRegistry
from src.data.secure_data_loader import SecureDatasetLoader
from src.data.validators import DataValidator
from src.utils.logger import configure_logging, get_logger


def main() -> int:
    config = load_config()
    configure_logging(
        logs_dir=config.paths.logs_dir,
        file_name=config.logging.file_name,
        level=config.logging.level,
        max_bytes=config.logging.max_bytes,
        backup_count=config.logging.backup_count,
    )
    logger = get_logger(__name__)
    logger.info("=== Module 1: Data Loading, Validation & Integration ===")

    registry = DataClassificationRegistry.from_csv(
        data_classification_csv=config.upstream_milestone1.data_classification_csv,
        data_lineage_csv=config.upstream_milestone1.data_lineage_csv,
    )

    loader = SecureDatasetLoader(config=config, classification_registry=registry)
    df, manifest = loader.load()
    manifest.to_json(config.paths.dataset_manifest_json)

    validator = DataValidator(config=config, registry=registry)
    report = validator.validate(df, manifest)
    report.to_json(config.paths.reports_m2_dir / "module1_validation_report.json")

    print(report.summary())
    print(f"\nDataset version: {manifest.dataset_version}")
    print(f"Dataset shape:    {df.shape}")
    print(f"Feature blocklist (never used as model features): {sorted(registry.feature_blocklist())}")

    if not report.passed:
        logger.error("Module 1 validation FAILED — halting before any downstream module runs.")
        return 1

    logger.info("Module 1 completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
