from __future__ import annotations

import json
import time

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.knowledge import KbChunk, KbDocument, KbFaq
from app.rag.embeddings import embed_query
from app.rag.store import search


def _keyword_hits(db: Session, query: str, top_k: int) -> list[dict]:
    like = f"%{query}%"
    faqs = (
        db.query(KbFaq)
        .filter(KbFaq.status == "published")
        .filter(
            or_(
                KbFaq.question.like(like),
                KbFaq.answer.like(like),
                KbFaq.similar_questions.like(like),
            )
        )
        .limit(top_k)
        .all()
    )
    chunks = db.query(KbChunk).filter(KbChunk.content.like(like)).limit(top_k).all()
    hits: list[dict] = []
    for faq in faqs:
        hits.append(
            {
                "source_type": "faq",
                "source_id": faq.id,
                "chunk_id": 0,
                "text": f"Q: {faq.question}\nA: {faq.answer}",
                "score": 0.55,
                "via": "keyword",
            }
        )
    for ch in chunks:
        hits.append(
            {
                "source_type": "doc",
                "source_id": ch.document_id,
                "chunk_id": ch.id,
                "text": ch.content,
                "score": 0.5,
                "via": "keyword",
            }
        )
    return hits


def _semantic_hits(query: str, top_k: int, threshold: float) -> list[dict]:
    vector = embed_query(query)
    semantic = search(vector, top_k=top_k, threshold=threshold)
    hits = []
    for h in semantic:
        hits.append(
            {
                "source_type": h["source_type"],
                "source_id": h["source_id"],
                "chunk_id": h.get("chunk_id"),
                "text": h["text"],
                "score": float(h["score"]),
                "via": "semantic",
            }
        )
    return hits


def _enrich(db: Session, items: list[dict]) -> list[dict]:
    for item in items:
        if item["source_type"] == "faq":
            faq = db.get(KbFaq, item["source_id"])
            item["title"] = faq.question if faq else f"FAQ#{item['source_id']}"
        else:
            doc = db.get(KbDocument, item["source_id"])
            item["title"] = doc.title if doc else f"文档#{item['source_id']}"
    return items


def retrieve(
    db: Session,
    query: str,
    mode: str = "hybrid",
    top_k: int = 5,
    threshold: float = 0.0,
) -> dict:
    """mode: hybrid | semantic | keyword"""
    t0 = time.perf_counter()
    semantic_n = 0
    keyword_n = 0
    merged: dict[str, dict] = {}

    if mode in ("hybrid", "semantic"):
        for h in _semantic_hits(query, top_k=max(top_k, 8), threshold=threshold):
            semantic_n += 1
            key = f"{h['source_type']}:{h['source_id']}:{h.get('chunk_id')}"
            merged[key] = h

    if mode in ("hybrid", "keyword"):
        for h in _keyword_hits(db, query, top_k=max(top_k, 8)):
            keyword_n += 1
            key = f"{h['source_type']}:{h['source_id']}:{h.get('chunk_id')}"
            if key not in merged:
                merged[key] = h
            else:
                merged[key]["score"] = max(float(merged[key]["score"]), float(h["score"]))
                merged[key]["via"] = "hybrid"

    out = sorted(merged.values(), key=lambda x: x["score"], reverse=True)[:top_k]
    out = _enrich(db, out)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    avg_rel = round(sum(float(x["score"]) for x in out) / len(out), 3) if out else 0.0
    return {
        "items": out,
        "stats": {
            "recall": len(out),
            "elapsed_ms": elapsed_ms,
            "avg_score": avg_rel,
            "semantic_count": semantic_n,
            "keyword_count": keyword_n,
            "mode": mode,
            "threshold": threshold,
            "top_k": top_k,
        },
    }


def hybrid_retrieve(db: Session, query: str, top_k: int = 5) -> list[dict]:
    return retrieve(db, query, mode="hybrid", top_k=top_k)["items"]


def faq_to_index_text(faq: KbFaq) -> str:
    try:
        similars = json.loads(faq.similar_questions or "[]")
    except json.JSONDecodeError:
        similars = []
    similar_block = "\n".join(f"相似问: {s}" for s in similars)
    return f"问题: {faq.question}\n{similar_block}\n答案: {faq.answer}".strip()
