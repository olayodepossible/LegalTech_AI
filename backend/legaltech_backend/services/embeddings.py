"""Text → embedding vector. Production: call your embedding API or local model."""

from __future__ import annotations

import hashlib


def stub_embedding(text: str, dimensions: int = 16) -> list[float]:
    """Deterministic pseudo-embedding for dev without a model server."""
    h = hashlib.sha256(text.encode()).digest()
    out: list[float] = []
    for i in range(dimensions):
        b = h[i % len(h)]
        out.append((b - 128) / 128.0)
    return out
