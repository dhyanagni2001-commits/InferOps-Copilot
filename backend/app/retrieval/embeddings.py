"""Dependency-free deterministic embeddings for local retrieval."""

import hashlib
import math


def embed_text(text: str, dimensions: int = 128) -> list[float]:
    vector = [0.0] * dimensions
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode()).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        vector[index] += -1.0 if digest[4] % 2 else 1.0
    length = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / length for value in vector]


def similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))
