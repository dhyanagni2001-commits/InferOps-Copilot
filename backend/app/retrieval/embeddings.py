"""Embedding providers shared by ingestion and query-time retrieval.

Documents and queries must be embedded by the same provider; every index records the
provider's ``model_id`` and searches refuse an index built by a different one.
"""

from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache
from typing import Protocol

from app.config import settings

TOKEN = re.compile(r"[a-z0-9]+")


class Embedder(Protocol):
    model_id: str
    dimensions: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashEmbedder:
    """Dependency-free signed feature hashing. Lexical only, but deterministic and offline."""

    def __init__(self, dimensions: int = 256) -> None:
        self.dimensions = dimensions
        self.model_id = f"feature-hash-v2-{dimensions}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = TOKEN.findall(text.lower())
        # Unigrams plus bigrams so phrases like "readiness probe" carry extra signal.
        for feature in tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]:
            digest = hashlib.sha256(feature.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            vector[index] += -1.0 if digest[4] % 2 else 1.0
        length = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / length for value in vector]


class TritonEmbedder:
    """Tokenize in Python and run the exported encoder (mean pooling + L2 norm) on Triton."""

    def __init__(self, tokenizer_path: str | None = None, max_tokens: int | None = None) -> None:
        from tokenizers import Tokenizer

        from app.inference.triton_client import TritonClient

        self.tokenizer = Tokenizer.from_file(tokenizer_path or settings.tokenizer_path)
        self.tokenizer.enable_truncation(max_tokens or settings.embedding_max_tokens)
        self.tokenizer.enable_padding()
        self.client = TritonClient()
        metadata = self.client.metadata()
        self.dimensions = int(metadata["outputs"][0]["shape"][-1])
        self.model_id = f"triton:{settings.triton_model}:{metadata.get('versions', ['?'])[-1]}:{self.dimensions}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), 16):
            encodings = self.tokenizer.encode_batch(texts[start:start + 16])
            vectors.extend(self.client.embed_tokens(
                [item.ids for item in encodings], [item.attention_mask for item in encodings]
            ))
        return vectors


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    if settings.embedding_backend == "triton":
        return TritonEmbedder()
    return HashEmbedder()


def similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))
