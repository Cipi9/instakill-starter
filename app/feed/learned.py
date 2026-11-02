"""NumPy scorer exported by the Week 5 learning lab."""
from pathlib import Path

import numpy as np


class LearnedScorer:
    def __init__(self, model_path: Path | None = None):
        path = model_path or Path(__file__).with_name("like_model.npz")
        with np.load(path, allow_pickle=False) as model:
            self._mu = np.asarray(model["mu"], dtype=float)
            self._sd = np.asarray(model["sd"], dtype=float)
            self._w1 = np.asarray(model["W1"], dtype=float)
            self._b1 = np.asarray(model["b1"], dtype=float)
            self._w2 = np.asarray(model["W2"], dtype=float)
            self._b2 = np.asarray(model["b2"], dtype=float)
            self.features = tuple(str(value) for value in model["features"])

    def predict(self, features: np.ndarray) -> np.ndarray:
        values = np.asarray(features, dtype=float)
        if values.ndim != 2 or values.shape[1] != len(self.features):
            raise ValueError(f"expected an array with {len(self.features)} features")
        standardized = (values - self._mu) / self._sd
        hidden = np.tanh(standardized @ self._w1 + self._b1)
        scores = hidden @ self._w2 + self._b2
        return 1.0 / (1.0 + np.exp(-np.clip(scores[:, 0], -60, 60)))
