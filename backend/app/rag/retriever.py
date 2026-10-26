from __future__ import annotations

import json
import re
import time

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.knowledge import KbChunk, KbDocument, KbFaq
from app.rag.embeddings import embed_query
from app.rag.store import search

# 过短、无检索价值的片段
_STOP = {
    "的",
    "了",
    "吗",
    "呢",
    "啊",
    "吧",
    "么",
    "什么",
    "怎么",
    "如何",
    "请问",
    "一下",
    "可以",
    "是不是",
}


def _query_terms(query: str) -> list[str]:
    """从中文问题里抽出可用于模糊匹配的词/片段。"""
    q = re.sub(r"\s+", "", (query or "").strip())
    if not q:
        return []

    terms: list[str] = [q]

    # 连续中文按 2～4 字滑窗
    for n in (4, 3, 2):
        if len(q) < n:
            continue
        for i in range(len(q) - n + 1):
            piece = q[i : i + n]
            if piece in _STOP:
                continue
            terms.append(piece)

    # 英文/数字单词
    for w in re.findall(r"[A-Za-z0-9_\-]{2,}", query or ""):
        terms.append(w)

    # 去重保序
    seen: set[str] = set()
    out: list[str] = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:24]


def _text_blob(faq: KbFaq | None = None, chunk_text: str = "") -> str:
    if faq is not None:
        return f"{faq.question}\n{faq.answer}\n{faq.similar_questions or ''}"
    return chunk_text or ""


def _term_score(blob: str, terms: list[str]) -> float:
    if not blob or not terms:
        return 0.0
    hit = sum(1 for t in terms if t in blob)
    if hit == 0:
        return 0.0
    # 全句命中给更高分；多词命中累加
    ratio = hit / max(len(terms), 1)
    base = 0.42 + 0.5 * ratio
    if terms and terms[0] in blob:
        base += 0.15
    return min(0.95, base)


def _keyword_hits(db: Session, query: str, top_k: int) -> list[dict]:
    terms = _query_terms(query)
    if not terms:
        return []

    # OR 多个片段，避免必须整句完全一致（「退款多久到账」也能打到「退款多久能到账」）
    faq_conds = []
    chunk_conds = []
    for t in terms[:12]:
        like = f"%{t}%"
        faq_conds.extend(
            [
                KbFaq.question.like(like),
                KbFaq.answer.like(like),
                KbFaq.similar_questions.like(like),
            ]
        )
        chunk_conds.append(KbChunk.content.like(like))

    faqs = (
        db.query(KbFaq)
        .filter(KbFaq.status == "published")
        .filter(or_(*faq_conds))
        .limit(max(top_k * 4, 20))
        .all()
    )
    chunks = (
        db.query(KbChunk)
        .filter(or_(*chunk_conds))
        .limit(max(top_k * 4, 20))
        .all()
    )

    scored: list[dict] = []
    for faq in faqs:
        blob = _text_blob(faq=faq)
        score = _term_score(blob, terms)
        if score <= 0:
            continue
        scored.append(
            {
                "source_type": "faq",
                "source_id": faq.id,
                "chunk_id": 0,
                "text": f"Q: {faq.question}\nA: {faq.answer}",
                "score": score,
                "via": "keyword",
            }
        )
    for ch in chunks:
        score = _term_score(ch.content, terms)
        if score <= 0:
            continue
        scored.append(
            {
                "source_type": "doc",
                "source_id": ch.document_id,
                "chunk_id": ch.id,
                "text": ch.content,
                "score": max(0.35, score - 0.05),
                "via": "keyword",
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[: max(top_k, 8)]


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
                # 语义+关键词同时命中，加权
                merged[key]["score"] = min(
                    0.99, max(float(merged[key]["score"]), float(h["score"])) + 0.08
                )
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
