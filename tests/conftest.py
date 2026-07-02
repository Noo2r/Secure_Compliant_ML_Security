"""Shared pytest fixtures for Milestone 2 tests.

Fixtures load the real ``config.yaml`` and Yara's real Milestone 1 report
CSVs (already present in the repo) rather than mocking them, so tests
exercise the actual integration contract instead of an idealized stand-in.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Module 4 (Differential Privacy) requires TensorFlow's legacy Keras 2 API
# (see src/privacy/tf_privacy_compat.py for the full explanation) and this
# must be configured before the FIRST import of tensorflow anywhere in the
# process. Importing it here, before any other import in this shared
# conftest, guarantees the setting is in effect for the whole pytest session
# regardless of which test file pytest happens to collect/import first --
# without this, Module 1-3's tests (which also use tensorflow, via
# src.models.keras_wrapper) could otherwise initialize TensorFlow in Keras 3
# mode first if collected before Module 4's tests, permanently breaking
# Module 4's DP optimizer construction for the rest of that pytest session.
import src.privacy.tf_privacy_compat  # noqa: E402,F401  (must precede other imports)

import pytest

from src.config.config_loader import AppConfig, load_config
from src.data.classification_registry import DataClassificationRegistry


@pytest.fixture(scope="session")
def app_config() -> AppConfig:
    return load_config()


@pytest.fixture(scope="session")
def classification_registry(app_config: AppConfig) -> DataClassificationRegistry:
    return DataClassificationRegistry.from_csv(
        data_classification_csv=app_config.upstream_milestone1.data_classification_csv,
        data_lineage_csv=app_config.upstream_milestone1.data_lineage_csv,
    )
