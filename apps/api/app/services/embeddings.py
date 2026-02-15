from __future__ import annotations

import hashlib
from typing import Iterable


def _hash_bytes(text: str) -> bytes:
    return hashlib.sha256(text.encode("utf-8")).digest()


def embed_text(text: str, *, dim: int = 1536) -> list[float]:
    """
    Deterministic embedding baseline (no external model required).

    This is NOT semantically strong, but it unblocks pgvector plumbing and API contracts.
    """
    seed = _hash_bytes(text or "")
    out: list[float] = []
    i = 0
    while len(out) < dim:
        b = seed[i % len(seed)]
        out.append((b / 255.0) * 2.0 - 1.0)
        i += 1
    return out


def embed_texts(texts: Iterable[str], *, dim: int = 1536) -> list[list[float]]:
    return [embed_text(t, dim=dim) for t in texts]

