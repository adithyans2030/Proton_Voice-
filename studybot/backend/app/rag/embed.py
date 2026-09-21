"""Text embeddings via fastembed (ONNX, CPU). Runs on CPU on purpose: the GPU's 4 GB is for the LLM."""
from pathlib import Path
from typing import Protocol, Sequence

import numpy as np


class EmbedderLike(Protocol):
    def embed_passages(self, texts: Sequence[str]) -> np.ndarray: ...
    def embed_query(self, query: str) -> np.ndarray: ...


class Embedder:
    # bge models retrieve better when short queries carry this instruction.
    QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

    def __init__(self, model_name: str, cache_dir: Path):
        self.model_name = model_name
        self.cache_dir = Path(cache_dir)
        self._model = None

    def _load(self):
        if self._model is None:
            from fastembed import TextEmbedding
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._model = TextEmbedding(self.model_name, cache_dir=str(self.cache_dir))
        return self._model

    @staticmethod
    def _normalize(matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        return (matrix / np.maximum(norms, 1e-12)).astype(np.float32)

    def embed_passages(self, texts: Sequence[str], batch_size: int = 32) -> np.ndarray:
        model = self._load()
        vectors = np.array(list(model.embed(list(texts), batch_size=batch_size)), dtype=np.float32)
        return self._normalize(vectors)

    def embed_query(self, query: str) -> np.ndarray:
        model = self._load()
        vector = np.array(list(model.embed([self.QUERY_PREFIX + query])), dtype=np.float32)
        return self._normalize(vector)[0]
