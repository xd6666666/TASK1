"""Embedding client: local Qwen OpenAI-compatible API, with deterministic mock fallback."""

from __future__ import annotations

import hashlib
import math

import httpx

from app.core.config import get_settings


def _mock_embed(text: str, dim: int) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    vals: list[float] = []
    seed = digest
    while len(vals) < dim:
        for b in seed:
            vals.append((b / 255.0) * 2 - 1)
            if len(vals) >= dim:
                break
        seed = hashlib.sha256(seed).digest()
    # L2 normalize
    norm = math.sqrt(sum(v * v for v in vals)) or 1.0
    return [v / norm for v in vals]


def embed_texts(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    if settings.llm_mock:
        return [_mock_embed(t, settings.embedding_dim) for t in texts]

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{settings.embedding_base_url.rstrip('/')}/embeddings",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={"model": settings.embedding_model, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            data = sorted(data, key=lambda x: x["index"])
            vectors = [row["embedding"] for row in data]
            if vectors:
                settings.embedding_dim = len(vectors[0])  # type: ignore[misc]
            return vectors
    except Exception:
        return [_mock_embed(t, settings.embedding_dim) for t in texts]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
