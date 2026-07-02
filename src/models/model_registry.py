"""Factory mapping a candidate model name to its estimator constructor and
Optuna hyperparameter search space.

Exactly the five model families named in the project brief -- Logistic
Regression, Random Forest, XGBoost, LightGBM, Neural Network -- nothing
added or substituted. Centralizing both "how to build it" and "what to
search over" per model here means :mod:`src.models.tune` and
:mod:`src.models.train` contain zero model-family-specific branching logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
import optuna
from lightgbm import LGBMClassifier
from sklearn.base import BaseEstimator
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier

from src.models.keras_wrapper import KerasClassifierWrapper


@dataclass(frozen=True)
class ModelSpec:
    """Everything needed to tune, build, and identify one candidate model."""

    name: str
    build_estimator: Callable[[dict[str, Any], float, int], BaseEstimator]
    suggest_params: Callable[[optuna.Trial], dict[str, Any]]


def _build_logistic_regression(params: dict[str, Any], scale_pos_weight: float, random_state: int) -> BaseEstimator:
    return LogisticRegression(
        C=params["C"],
        solver="lbfgs",  # L2 penalty is this solver's (and LogisticRegression's) default
        # lbfgs does not converge on this data at ANY C in the search range --
        # confirmed empirically: n_iter_ always equals max_iter exactly,
        # whether max_iter is 200 or 3000. Raising max_iter therefore buys
        # zero fit-quality improvement while multiplying runtime linearly
        # (measured: ~3s/fit at 200 vs ~50s/fit at 3000, on 66K rows x 202
        # features). Capped at a fixed, modest budget deliberately -- this
        # is a hyperparameter *search* fit, not the final model, and relative
        # CV ranking across trials is what matters here, not perfect
        # convergence on every trial.
        max_iter=200,
        class_weight="balanced",
        random_state=random_state,
    )


def _suggest_logistic_regression(trial: optuna.Trial) -> dict[str, Any]:
    return {"C": trial.suggest_float("C", 1e-3, 1e2, log=True)}


def _build_random_forest(params: dict[str, Any], scale_pos_weight: float, random_state: int) -> BaseEstimator:
    return RandomForestClassifier(
        n_estimators=params["n_estimators"],
        max_depth=params["max_depth"],
        min_samples_leaf=params["min_samples_leaf"],
        max_features=params["max_features"],
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=random_state,
    )


def _suggest_random_forest(trial: optuna.Trial) -> dict[str, Any]:
    return {
        "n_estimators": trial.suggest_int("n_estimators", 100, 400, step=50),
        "max_depth": trial.suggest_int("max_depth", 4, 20),
        "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 50),
        "max_features": trial.suggest_categorical("max_features", ["sqrt", "log2"]),
    }


def _build_xgboost(params: dict[str, Any], scale_pos_weight: float, random_state: int) -> BaseEstimator:
    return XGBClassifier(
        n_estimators=params["n_estimators"],
        max_depth=params["max_depth"],
        learning_rate=params["learning_rate"],
        subsample=params["subsample"],
        colsample_bytree=params["colsample_bytree"],
        min_child_weight=params["min_child_weight"],
        scale_pos_weight=scale_pos_weight,
        tree_method="hist",
        eval_metric="aucpr",
        n_jobs=-1,
        random_state=random_state,
    )


def _suggest_xgboost(trial: optuna.Trial) -> dict[str, Any]:
    return {
        "n_estimators": trial.suggest_int("n_estimators", 100, 500, step=50),
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
    }


def _build_lightgbm(params: dict[str, Any], scale_pos_weight: float, random_state: int) -> BaseEstimator:
    return LGBMClassifier(
        n_estimators=params["n_estimators"],
        num_leaves=params["num_leaves"],
        learning_rate=params["learning_rate"],
        subsample=params["subsample"],
        colsample_bytree=params["colsample_bytree"],
        min_child_samples=params["min_child_samples"],
        scale_pos_weight=scale_pos_weight,
        n_jobs=-1,
        random_state=random_state,
        verbosity=-1,
    )


def _suggest_lightgbm(trial: optuna.Trial) -> dict[str, Any]:
    return {
        "n_estimators": trial.suggest_int("n_estimators", 100, 500, step=50),
        "num_leaves": trial.suggest_int("num_leaves", 15, 255),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "min_child_samples": trial.suggest_int("min_child_samples", 5, 100),
    }


def _build_neural_network(params: dict[str, Any], scale_pos_weight: float, random_state: int) -> BaseEstimator:
    return KerasClassifierWrapper(
        n_layers=params["n_layers"],
        units=params["units"],
        dropout=params["dropout"],
        learning_rate=params["learning_rate"],
        batch_size=params["batch_size"],
        epochs=params["epochs"],
        class_weight_positive=scale_pos_weight,
        random_state=random_state,
    )


def _suggest_neural_network(trial: optuna.Trial) -> dict[str, Any]:
    return {
        "n_layers": trial.suggest_int("n_layers", 1, 3),
        "units": trial.suggest_categorical("units", [16, 32, 64, 128]),
        "dropout": trial.suggest_float("dropout", 0.0, 0.5),
        "learning_rate": trial.suggest_float("learning_rate", 1e-4, 1e-2, log=True),
        "batch_size": trial.suggest_categorical("batch_size", [128, 256, 512]),
        "epochs": trial.suggest_int("epochs", 10, 30),
    }


_MODEL_SPECS: dict[str, ModelSpec] = {
    "logistic_regression": ModelSpec("logistic_regression", _build_logistic_regression, _suggest_logistic_regression),
    "random_forest": ModelSpec("random_forest", _build_random_forest, _suggest_random_forest),
    "xgboost": ModelSpec("xgboost", _build_xgboost, _suggest_xgboost),
    "lightgbm": ModelSpec("lightgbm", _build_lightgbm, _suggest_lightgbm),
    "neural_network": ModelSpec("neural_network", _build_neural_network, _suggest_neural_network),
}


def get_model_spec(name: str) -> ModelSpec:
    if name not in _MODEL_SPECS:
        raise ValueError(f"Unknown candidate model '{name}'. Available: {sorted(_MODEL_SPECS)}")
    return _MODEL_SPECS[name]


def compute_scale_pos_weight(y: np.ndarray) -> float:
    """Ratio of negative-to-positive samples, used by XGBoost/LightGBM's imbalance weighting."""
    y = np.asarray(y)
    positive_count = max(int(y.sum()), 1)
    negative_count = len(y) - positive_count
    return negative_count / positive_count
