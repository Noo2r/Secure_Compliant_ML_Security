"""Environment setup required to use TensorFlow Privacy on this project's
TensorFlow 2.20 installation.

Two real, verified compatibility gaps exist between ``tensorflow-privacy``
0.8.11 (the latest release on PyPI at the time of writing) and TensorFlow
2.20 -- documented here, with the exact errors encountered, so the
workaround is not a mystery later:

1. ``tensorflow_privacy``'s top-level ``__init__.py`` eagerly imports its
   legacy TF1 ``Estimator``-based API, which itself imports
   ``tensorflow_estimator``, which raises
   ``ImportError: cannot import name 'estimator_training' from
   'tensorflow.python.distribute'`` on TensorFlow 2.20 -- that TF1 codepath
   was never updated for modern TF internals. This project never uses the
   Estimator API, only the Keras optimizers and the privacy accountant, so
   this is bypassed via the library's own documented escape hatch: setting
   ``sys.skip_tf_privacy_import`` before import skips ALL of the top-level
   package's eager imports, and the specific symbols actually needed are
   imported directly from their submodules instead (see
   :mod:`src.privacy.privacy_accountant` and :mod:`src.privacy.dp_model`).
2. ``tensorflow_privacy``'s Keras optimizers (``DPKerasAdamOptimizer`` etc.)
   subclass ``keras.optimizers.legacy.Optimizer``, which does not exist in
   Keras 3 (TensorFlow's default optimizer API since TF 2.16) and raises
   ``ImportError: keras.optimizers.legacy is not supported in Keras 3``. The
   fix -- directly suggested by that error message -- is installing the
   ``tf_keras`` compatibility package and setting the
   ``TF_USE_LEGACY_KERAS=1`` environment variable, which makes
   ``from tensorflow import keras`` resolve to Keras 2 everywhere in the
   process for the remainder of its lifetime.

**Both fixes must take effect before the first ``import tensorflow``
anywhere in the process** -- Keras backend selection happens once, at first
import, and cannot be changed afterward. Every module in this project that
touches TensorFlow (directly or by calling into
:mod:`src.models.keras_wrapper`) must therefore import this module FIRST,
before any other import that could transitively import TensorFlow. This is
also why ``tests/conftest.py`` imports this module at its own top, ahead of
every other import -- so the setting is in effect for the whole pytest
session regardless of which test file pytest happens to collect first.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")
sys.skip_tf_privacy_import = True  # type: ignore[attr-defined]
