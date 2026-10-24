from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.knowledge import KbChunk, KbDocument, KbFaq
from app.rag.embeddings import embed_texts
from app.rag.retriever import faq_to_index_text
from app.rag.store import delete_by_ids, upsert_vectors
from app.services.documents import chunk_text, extract_text


def index_faq(db: Session, faq: KbFaq) -> None:
    text = faq_to_index_text(faq)
    vec = embed_texts([text])[0]
    vid = f"faq-{faq.id}"
    delete_by_ids([vid])
    upsert_vectors(
        [
            {
                "id": vid,
                "source_type": "faq",
                "source_id": faq.id,
                "chunk_id": 0,
                "text": text[:3900],
                "embedding": vec,
            }
        ]
    )


def remove_faq_index(faq_id: int) -> None:
    delete_by_ids([f"faq-{faq_id}"])


def index_document(db: Session, doc: KbDocument) -> None:
    # clear old chunks
    old = db.query(KbChunk).filter(KbChunk.document_id == doc.id).all()
    if old:
        delete_by_ids([c.milvus_id for c in old if c.milvus_id])
        for c in old:
            db.delete(c)
        db.flush()

    try:
        raw = extract_text(doc.filepath, doc.content_type, doc.filename)
        pieces = chunk_text(raw)
        if not pieces:
            doc.status = "failed"
            doc.summary = "未能从文件中提取到文本"
            doc.chunk_count = 0
            db.commit()
            return

        vectors = embed_texts(pieces)
        rows = []
        for i, (piece, vec) in enumerate(zip(pieces, vectors)):
            mid = f"doc-{doc.id}-{i}"
            chunk = KbChunk(
                document_id=doc.id,
                chunk_index=i,
                content=piece,
                milvus_id=mid,
            )
            db.add(chunk)
            db.flush()
            rows.append(
                {
                    "id": mid,
                    "source_type": "doc",
                    "source_id": doc.id,
                    "chunk_id": chunk.id,
                    "text": piece[:3900],
                    "embedding": vec,
                }
            )
        upsert_vectors(rows)
        doc.chunk_count = len(pieces)
        doc.summary = pieces[0][:200]
        doc.status = "ready"
        db.commit()
    except Exception as exc:  # noqa: BLE001
        doc.status = "failed"
        doc.summary = str(exc)[:500]
        db.commit()


def remove_document_index(db: Session, doc_id: int) -> None:
    chunks = db.query(KbChunk).filter(KbChunk.document_id == doc_id).all()
    delete_by_ids([c.milvus_id for c in chunks if c.milvus_id])
    for c in chunks:
        db.delete(c)
