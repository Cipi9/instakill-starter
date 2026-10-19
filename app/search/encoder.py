"""Embedding adapter used by semantic search."""
from collections.abc import Sequence
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

Vector = NDArray[np.float32]


class TextEncoder(Protocol):
    def encode(self, texts: Sequence[str]) -> NDArray[np.float32]:
        """Return one embedding vector for each input text."""


class SentenceTransformerEncoder:
    """Lazy adapter around the compact pretrained sentence-transformer model."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._model = None

    def encode(self, texts: Sequence[str]) -> NDArray[np.float32]:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return np.asarray(self._model.encode(list(texts)), dtype=np.float32)
