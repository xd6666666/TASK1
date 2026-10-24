"""Vector store backed by Milvus Lite (local file) or remote Milvus URI."""

from __future__ import annotations

from typing import Any

from pymilvus import DataType, MilvusClient

from app.core.config import get_settings

_client: MilvusClient | None = None


def get_client() -> MilvusClient:
    global _client
    if _client is None:
        settings = get_settings()
        uri = settings.vector_uri
        if uri.startswith("http://") or uri.startswith("https://"):
            _client = MilvusClient(uri=uri)
        else:
            from pathlib import Path

            path = Path(uri).expanduser().resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            _client = MilvusClient(uri=str(path))
        _ensure_collection(_client)
    return _client


def _ensure_collection(client: MilvusClient) -> None:
    settings = get_settings()
    name = settings.milvus_collection
    if client.has_collection(name):
        return
    schema = client.create_schema(auto_id=False, enable_dynamic_field=True)
    schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=64)
    schema.add_field("source_type", DataType.VARCHAR, max_length=16)  # faq | doc
    schema.add_field("source_id", DataType.INT64)
    schema.add_field("chunk_id", DataType.INT64)
    schema.add_field("text", DataType.VARCHAR, max_length=4000)
    schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=settings.embedding_dim)
    index_params = client.prepare_index_params()
    index_params.add_index(field_name="embedding", index_type="AUTOINDEX", metric_type="IP")
    client.create_collection(collection_name=name, schema=schema, index_params=index_params)


def upsert_vectors(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    client = get_client()
    settings = get_settings()
    client.upsert(collection_name=settings.milvus_collection, data=rows)


def delete_by_ids(ids: list[str]) -> None:
    if not ids:
        return
    client = get_client()
    settings = get_settings()
    client.delete(collection_name=settings.milvus_collection, ids=ids)


def search(vector: list[float], top_k: int = 5, threshold: float = 0.0) -> list[dict[str, Any]]:
    client = get_client()
    settings = get_settings()
    name = settings.milvus_collection
    try:
        client.load_collection(collection_name=name)
    except Exception:
        pass
    results = client.search(
        collection_name=name,
        data=[vector],
        limit=top_k,
        output_fields=["source_type", "source_id", "chunk_id", "text"],
    )
    hits: list[dict[str, Any]] = []
    for group in results:
        for hit in group:
            score = float(hit.get("distance", hit.get("score", 0)))
            if score < threshold:
                continue
            entity = hit.get("entity") or {}
            hits.append(
                {
                    "id": hit.get("id"),
                    "score": score,
                    "source_type": entity.get("source_type"),
                    "source_id": entity.get("source_id"),
                    "chunk_id": entity.get("chunk_id"),
                    "text": entity.get("text"),
                }
            )
    return hits
