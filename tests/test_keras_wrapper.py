import numpy as np

from src.models.keras_wrapper import KerasClassifierWrapper


def _tiny_dataset(n: int = 120):
    rng = np.random.default_rng(0)
    X = rng.normal(size=(n, 4)).astype("float32")
    y = (X[:, 0] > 0).astype("float32")
    return X, y


def test_keras_wrapper_fit_predict_proba_shape() -> None:
    X, y = _tiny_dataset()
    model = KerasClassifierWrapper(n_layers=1, units=8, epochs=2, batch_size=32, random_state=42)
    model.fit(X, y)
    proba = model.predict_proba(X)
    assert proba.shape == (len(X), 2)
    np.testing.assert_allclose(proba.sum(axis=1), 1.0, atol=1e-5)


def test_keras_wrapper_predict_returns_binary_labels() -> None:
    X, y = _tiny_dataset()
    model = KerasClassifierWrapper(n_layers=1, units=8, epochs=2, batch_size=32, random_state=42)
    model.fit(X, y)
    predictions = model.predict(X)
    assert set(np.unique(predictions)).issubset({0, 1})


def test_keras_wrapper_survives_joblib_round_trip(tmp_path) -> None:
    import joblib

    X, y = _tiny_dataset()
    model = KerasClassifierWrapper(n_layers=1, units=8, epochs=2, batch_size=32, random_state=42)
    model.fit(X, y)
    original_proba = model.predict_proba(X)

    path = tmp_path / "keras_model.joblib"
    joblib.dump(model, path)
    reloaded = joblib.load(path)
    reloaded_proba = reloaded.predict_proba(X)

    np.testing.assert_allclose(original_proba, reloaded_proba, atol=1e-5)


def test_keras_wrapper_applies_class_weight_without_error() -> None:
    X, y = _tiny_dataset()
    model = KerasClassifierWrapper(n_layers=1, units=8, epochs=2, batch_size=32, class_weight_positive=5.0, random_state=42)
    model.fit(X, y)  # must not raise (class_weight + sample_weight=None together)
    assert model.is_fitted_ is True
