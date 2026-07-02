"""A thin, sklearn-compatible, joblib-picklable wrapper around a Keras model.

Keras/TensorFlow models are not natively sklearn estimators (no
``predict_proba`` returning a 2-column array) and are not directly
joblib-picklable in a way that survives a plain ``joblib.dump``/``load``
round-trip reliably across processes. This wrapper closes both gaps so the
Neural Network candidate can be handled through the exact same
``InferenceBundle`` mechanism as every scikit-learn/XGBoost/LightGBM model,
with no special-casing needed anywhere else in Module 3.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin


class KerasClassifierWrapper(BaseEstimator, ClassifierMixin):
    """Wraps a compiled binary-classification Keras model for sklearn-style use.

    Deliberately built architecturally simple (plain ``Dense`` layers, no
    ``BatchNormalization``) so the same architecture can later be trained
    with TensorFlow Privacy's DP-SGD optimizer in Module 4 -- BatchNorm
    complicates the per-example gradient computation DP-SGD relies on.
    """

    def __init__(
        self,
        n_layers: int = 2,
        units: int = 64,
        dropout: float = 0.2,
        learning_rate: float = 1e-3,
        batch_size: int = 256,
        epochs: int = 20,
        class_weight_positive: float = 1.0,
        random_state: int = 42,
    ) -> None:
        self.n_layers = n_layers
        self.units = units
        self.dropout = dropout
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.epochs = epochs
        # Weight applied to the positive (fraud) class in the loss function --
        # analogous to scale_pos_weight in XGBoost/LightGBM. Without this, the
        # ~3.5% positive rate would bias the network toward always predicting
        # "not fraud".
        self.class_weight_positive = class_weight_positive
        self.random_state = random_state

    def _build_model(self, n_features: int):
        import tensorflow as tf
        from tensorflow import keras

        tf.random.set_seed(self.random_state)
        layers = [keras.layers.Input(shape=(n_features,))]
        for _ in range(self.n_layers):
            layers.append(keras.layers.Dense(self.units, activation="relu"))
            if self.dropout > 0:
                layers.append(keras.layers.Dropout(self.dropout))
        layers.append(keras.layers.Dense(1, activation="sigmoid"))
        model = keras.Sequential(layers)
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=self.learning_rate),
            loss="binary_crossentropy",
            metrics=[keras.metrics.AUC(name="pr_auc", curve="PR")],
        )
        return model

    def fit(self, X: np.ndarray, y: np.ndarray, sample_weight: Optional[np.ndarray] = None) -> "KerasClassifierWrapper":
        X = np.asarray(X, dtype="float32")
        y = np.asarray(y, dtype="float32")
        self.model_ = self._build_model(n_features=X.shape[1])
        self.model_.fit(
            X, y,
            sample_weight=sample_weight,
            class_weight={0: 1.0, 1: self.class_weight_positive},
            batch_size=self.batch_size,
            epochs=self.epochs,
            verbose=0,
        )
        self.classes_ = np.array([0, 1])
        self.is_fitted_ = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype="float32")
        positive_proba = self.model_.predict(X, verbose=0).ravel()
        return np.column_stack([1 - positive_proba, positive_proba])

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)

    # ------------------------------------------------------------------
    # Custom pickling: Keras models don't survive plain joblib/pickle
    # reliably, so serialize via Keras's own save/load format instead.
    # ------------------------------------------------------------------
    def __getstate__(self) -> dict:
        state = self.__dict__.copy()
        model = state.pop("model_", None)
        if model is not None:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir) / "model.keras"
                model.save(tmp_path)
                state["_serialized_model_bytes"] = tmp_path.read_bytes()
        return state

    def __setstate__(self, state: dict) -> None:
        serialized = state.pop("_serialized_model_bytes", None)
        self.__dict__.update(state)
        if serialized is not None:
            from tensorflow import keras
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir) / "model.keras"
                tmp_path.write_bytes(serialized)
                self.model_ = keras.models.load_model(tmp_path)
