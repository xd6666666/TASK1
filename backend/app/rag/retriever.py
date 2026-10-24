from __future__ import annotations

import json

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.knowledge import KbChunk, KbDocument, KbFaq
from app.rag.embeddings import embed_query
from app.rag.store import search


def hybrid_retrieve(db: Session, query: str, top_k: int = 5) -> list[dict]:
    """Semantic (Milvus) + keyword (MySQL/SQLite LIKE) fusion."""
    vector = embed_query(query)
    semantic = search(vector, top_k=top_k, threshold=0.0)

    # keyword over FAQ + chunks
    like = f"%{query}%"
    faqs = (
        db.query(KbFaq)
        .filter(KbFaq.status == "published")
        .filter(or_(KbFaq.question.like(like), KbFaq.answer.like(like), KbFaq.similar_questions.like(like)))
        .limit(top_k)
        .all()
    )
    chunks = (
        db.query(KbChunk)
        .filter(KbChunk.content.like(like))
        .limit(top_k)
        .all()
    )

    merged: dict[str, dict] = {}
    for h in semantic:
        key = f"{h['source_type']}:{h['source_id']}:{h.get('chunk_id')}"
        merged[key] = {
            "source_type": h["source_type"],
            "source_id": h["source_id"],
            "chunk_id": h.get("chunk_id"),
            "text": h["text"],
            "score": float(h["score"]),
            "via": "semantic",
        }

    for faq in faqs:
        key = f"faq:{faq.id}:0"
        if key not in merged:
            merged[key] = {
                "source_type": "faq",
                "source_id": faq.id,
                "chunk_id": 0,
                "text": f"Q: {faq.question}\nA: {faq.answer}",
                "score": 0.55,
                "via": "keyword",
            }
        else:
            merged[key]["score"] = max(merged[key]["score"], 0.55)
            merged[key]["via"] = "hybrid"

    for ch in chunks:
        key = f"doc:{ch.document_id}:{ch.id}"
        if key not in merged:
            merged[key] = {
                "source_type": "doc",
                "source_id": ch.document_id,
                "chunk_id": ch.id,
                "text": ch.content,
                "score": 0.5,
                "via": "keyword",
            }

    # enrich titles
    out = sorted(merged.values(), key=lambda x: x["score"], reverse=True)[:top_k]
    for item in out:
        if item["source_type"] == "faq":
            faq = db.get(KbFaq, item["source_id"])
            item["title"] = faq.question if faq else f"FAQ#{item['source_id']}"
        else:
            doc = db.get(KbDocument, item["source_id"])
            item["title"] = doc.title if doc else f"文档#{item['source_id']}"
    return out


def faq_to_index_text(faq: KbFaq) -> str:
    try:
        similars = json.loads(faq.similar_questions or "[]")
    except json.JSONDecodeError:
        similars = []
    similar_block = "\n".join(f"相似问: {s}" for s in similars)
    return f"问题: {faq.question}\n{similar_block}\n答案: {faq.answer}".strip()
