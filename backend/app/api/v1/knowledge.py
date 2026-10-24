from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.knowledge import KbCategory, KbChunk, KbDocument, KbFaq
from app.models.user import User
from app.schemas.common import ok
from app.schemas.knowledge import ChunkOut, DocOut, FaqIn, FaqOut
from app.services.indexer import index_document, index_faq, remove_document_index, remove_faq_index

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def _faq_out(faq: KbFaq) -> dict:
    try:
        similars = json.loads(faq.similar_questions or "[]")
    except json.JSONDecodeError:
        similars = []
    return FaqOut(
        id=faq.id,
        question=faq.question,
        answer=faq.answer,
        similar_questions=similars,
        category_id=faq.category_id,
        status=faq.status,
        created_at=faq.created_at,
        updated_at=faq.updated_at,
    ).model_dump()


@router.get("/categories")
def list_categories(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.query(KbCategory).order_by(KbCategory.sort.asc(), KbCategory.id.asc()).all()
    return ok([{"id": r.id, "name": r.name, "sort": r.sort} for r in rows])


# ---------- FAQ ----------
@router.get("/faqs")
def list_faqs(
    q: str = "",
    category_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(KbFaq)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (KbFaq.question.like(like))
            | (KbFaq.answer.like(like))
            | (KbFaq.similar_questions.like(like))
        )
    if category_id:
        query = query.filter(KbFaq.category_id == category_id)
    total = query.count()
    rows = (
        query.order_by(KbFaq.id.desc())
        .offset(max(page - 1, 0) * page_size)
        .limit(page_size)
        .all()
    )
    return ok({"total": total, "list": [_faq_out(r) for r in rows]})


@router.post("/faqs")
def create_faq(
    body: FaqIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    faq = KbFaq(
        question=body.question,
        answer=body.answer,
        similar_questions=json.dumps(body.similar_questions, ensure_ascii=False),
        category_id=body.category_id,
        status=body.status,
        owner_id=user.id,
    )
    db.add(faq)
    db.commit()
    db.refresh(faq)
    if faq.status == "published":
        index_faq(db, faq)
    return ok(_faq_out(faq))


@router.put("/faqs/{faq_id}")
def update_faq(
    faq_id: int,
    body: FaqIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    faq = db.get(KbFaq, faq_id)
    if not faq:
        raise HTTPException(404, "FAQ 不存在")
    faq.question = body.question
    faq.answer = body.answer
    faq.similar_questions = json.dumps(body.similar_questions, ensure_ascii=False)
    faq.category_id = body.category_id
    faq.status = body.status
    db.commit()
    db.refresh(faq)
    if faq.status == "published":
        index_faq(db, faq)
    else:
        remove_faq_index(faq.id)
    return ok(_faq_out(faq))


@router.delete("/faqs/{faq_id}")
def delete_faq(
    faq_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    faq = db.get(KbFaq, faq_id)
    if not faq:
        raise HTTPException(404, "FAQ 不存在")
    remove_faq_index(faq.id)
    db.delete(faq)
    db.commit()
    return ok(True)


# ---------- Documents ----------
@router.get("/documents")
def list_documents(
    q: str = "",
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(KbDocument)
    if q:
        like = f"%{q}%"
        query = query.filter((KbDocument.title.like(like)) | (KbDocument.filename.like(like)))
    total = query.count()
    rows = (
        query.order_by(KbDocument.id.desc())
        .offset(max(page - 1, 0) * page_size)
        .limit(page_size)
        .all()
    )
    return ok(
        {
            "total": total,
            "list": [DocOut.model_validate(r).model_dump() for r in rows],
        }
    )


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(""),
    category_id: int | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = get_settings()
    upload_root = Path(settings.upload_dir)
    upload_root.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "file.bin").suffix.lower()
    if suffix not in {".pdf", ".docx", ".doc", ".txt", ".md"}:
        raise HTTPException(400, "仅支持 pdf / docx / txt / md")
    stored = f"{uuid.uuid4().hex}{suffix}"
    dest = upload_root / stored
    content = await file.read()
    dest.write_bytes(content)

    doc = KbDocument(
        title=title or (file.filename or stored),
        filename=file.filename or stored,
        filepath=str(dest),
        content_type=file.content_type or "",
        status="processing",
        category_id=category_id,
        owner_id=user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    index_document(db, doc)
    db.refresh(doc)
    return ok(DocOut.model_validate(doc).model_dump())


@router.get("/documents/{doc_id}")
def get_document(
    doc_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    doc = db.get(KbDocument, doc_id)
    if not doc:
        raise HTTPException(404, "文档不存在")
    chunks = (
        db.query(KbChunk)
        .filter(KbChunk.document_id == doc_id)
        .order_by(KbChunk.chunk_index.asc())
        .all()
    )
    return ok(
        {
            "document": DocOut.model_validate(doc).model_dump(),
            "chunks": [ChunkOut.model_validate(c).model_dump() for c in chunks],
        }
    )


@router.get("/documents/{doc_id}/file")
def preview_file(
    doc_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    doc = db.get(KbDocument, doc_id)
    if not doc or not Path(doc.filepath).exists():
        raise HTTPException(404, "文件不存在")
    return FileResponse(
        doc.filepath,
        filename=doc.filename,
        media_type=doc.content_type or "application/octet-stream",
    )


@router.delete("/documents/{doc_id}")
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    doc = db.get(KbDocument, doc_id)
    if not doc:
        raise HTTPException(404, "文档不存在")
    remove_document_index(db, doc.id)
    path = Path(doc.filepath)
    db.delete(doc)
    db.commit()
    if path.exists():
        path.unlink(missing_ok=True)
    return ok(True)
