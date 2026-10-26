from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.inspect_agent import inspect_conversation
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.qa import QaResult, QaRule
from app.models.user import User
from app.schemas.common import ok

router = APIRouter(prefix="/qa", tags=["qa"])


class RuleIn(BaseModel):
    name: str = Field(min_length=1)
    group_name: str = "服务规范"
    description: str = ""
    severity: str = "medium"
    enabled: bool = True
    check_prompt: str = ""


class ReviewIn(BaseModel):
    note: str = ""
    pass_ok: bool = True


def _rule_out(r: QaRule) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "group_name": r.group_name,
        "description": r.description,
        "severity": r.severity,
        "enabled": r.enabled,
        "check_prompt": r.check_prompt,
    }


def _result_out(db: Session, r: QaResult) -> dict:
    conv = db.get(Conversation, r.conversation_id)
    cust = db.get(Customer, conv.customer_id) if conv else None
    try:
        hits = json.loads(r.hit_rules or "[]")
    except json.JSONDecodeError:
        hits = []
    return {
        "id": r.id,
        "conversation_id": r.conversation_id,
        "session_no": conv.session_no if conv else "",
        "customer_name": cust.name if cust else "",
        "agent_id": conv.agent_id if conv else None,
        "score": r.score,
        "level": r.level,
        "hit_rules": hits,
        "summary": r.summary,
        "status": r.status,
        "review_note": r.review_note,
        "created_at": r.created_at,
    }


@router.get("/overview")
def qa_overview(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.query(QaResult).order_by(QaResult.id.desc()).all()
    total_conv = db.query(Conversation).count() or 1
    covered = len({r.conversation_id for r in rows})
    avg_score = round(sum(r.score for r in rows) / len(rows), 1) if rows else 0
    risk = sum(1 for r in rows if r.level == "risk")
    pending = sum(1 for r in rows if r.status == "pending_review")
    return ok(
        {
            "kpi": {
                "coverage": round(covered / total_conv * 100, 1),
                "avg_score": avg_score,
                "risk_count": risk,
                "pending_review": pending,
                "sampled": len(rows),
                "total_sessions": total_conv,
            },
            "results": [_result_out(db, r) for r in rows[:50]],
            "radar": {
                "服务态度": 88,
                "响应时效": 92,
                "问题解决": 85,
                "合规表达": 90,
                "知识引用": 80,
            },
            "rule_hits": _rule_hit_top(rows),
        }
    )


def _rule_hit_top(rows: list[QaResult]) -> list[dict]:
    from collections import Counter

    c: Counter[str] = Counter()
    for r in rows:
        try:
            hits = json.loads(r.hit_rules or "[]")
        except json.JSONDecodeError:
            hits = []
        c.update(hits)
    return [{"name": k, "value": v} for k, v in c.most_common(5)]


@router.get("/rules")
def list_rules(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.query(QaRule).order_by(QaRule.id.asc()).all()
    return ok([_rule_out(r) for r in rows])


@router.post("/rules")
def create_rule(
    body: RuleIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    r = QaRule(**body.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return ok(_rule_out(r))


@router.put("/rules/{rule_id}")
def update_rule(
    rule_id: int,
    body: RuleIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    r = db.get(QaRule, rule_id)
    if not r:
        raise HTTPException(404, "规则不存在")
    for k, v in body.model_dump().items():
        setattr(r, k, v)
    db.commit()
    return ok(_rule_out(r))


@router.delete("/rules/{rule_id}")
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    r = db.get(QaRule, rule_id)
    if not r:
        raise HTTPException(404, "规则不存在")
    db.delete(r)
    db.commit()
    return ok(True)


@router.get("/reviews")
def list_reviews(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = (
        db.query(QaResult)
        .filter(QaResult.status == "pending_review")
        .order_by(QaResult.id.desc())
        .all()
    )
    return ok([_result_out(db, r) for r in rows])


@router.post("/reviews/{result_id}")
def review_result(
    result_id: int,
    body: ReviewIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    r = db.get(QaResult, result_id)
    if not r:
        raise HTTPException(404, "记录不存在")
    r.status = "resolved"
    r.reviewer_id = user.id
    r.review_note = body.note or ("复核通过" if body.pass_ok else "复核驳回，需复训")
    if not body.pass_ok:
        r.level = "risk"
    db.commit()
    return ok(_result_out(db, r))


@router.post("/inspect")
def run_inspect(
    conversation_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Inspect one conversation or sample all active/closed."""
    if conversation_id:
        ids = [conversation_id]
    else:
        ids = [c.id for c in db.query(Conversation).order_by(Conversation.id.desc()).limit(20).all()]
    created = []
    for cid in ids:
        # skip if already inspected recently
        exists = (
            db.query(QaResult)
            .filter(QaResult.conversation_id == cid)
            .order_by(QaResult.id.desc())
            .first()
        )
        if exists and conversation_id is None:
            continue
        row = inspect_conversation(db, cid)
        created.append(_result_out(db, row))
    if conversation_id and not created:
        row = inspect_conversation(db, conversation_id)
        created.append(_result_out(db, row))
    return ok({"count": len(created), "results": created})
