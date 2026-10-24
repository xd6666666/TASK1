from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.qa_agent import run_suggest
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.conversation import CHANNEL_LABELS, Conversation, Message
from app.models.customer import Customer
from app.models.user import User
from app.schemas.common import ok
from app.schemas.workspace import AiSuggestOut, MessageOut, SendMessageIn

router = APIRouter(prefix="/workspace", tags=["workspace"])


def _conv_out(db: Session, conv: Conversation) -> dict:
    cust = db.get(Customer, conv.customer_id)
    last = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.id.desc())
        .first()
    )
    return {
        "id": conv.id,
        "session_no": conv.session_no,
        "channel": conv.channel,
        "channel_label": CHANNEL_LABELS.get(conv.channel, conv.channel),
        "status": conv.status,
        "subject": conv.subject,
        "customer_id": conv.customer_id,
        "customer_name": cust.name if cust else "",
        "customer_level": cust.level if cust else "",
        "customer_phone": cust.phone_mask if cust else "",
        "customer_tags": cust.tags if cust else "",
        "last_message": last.content if last else "",
        "updated_at": conv.updated_at,
        "created_at": conv.created_at,
    }


@router.get("/conversations")
def list_conversations(
    status: str = "all",
    channel: str = "all",
    q: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Conversation)
    if status != "all":
        query = query.filter(Conversation.status == status)
    if channel != "all":
        query = query.filter(Conversation.channel == channel)
    rows = query.order_by(Conversation.updated_at.desc()).all()
    out = [_conv_out(db, c) for c in rows]
    if q:
        ql = q.lower()
        out = [
            x
            for x in out
            if ql in x["customer_name"].lower()
            or ql in x["session_no"].lower()
            or ql in (x["last_message"] or "").lower()
            or ql in x["channel_label"].lower()
        ]
    return ok(out)


@router.get("/conversations/{conv_id}")
def get_conversation(
    conv_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    conv = db.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(404, "会话不存在")
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conv_id)
        .order_by(Message.id.asc())
        .all()
    )
    return ok(
        {
            "conversation": _conv_out(db, conv),
            "messages": [MessageOut.model_validate(m).model_dump() for m in msgs],
        }
    )


@router.get("/conversations/{conv_id}/ai-suggest")
def ai_suggest(
    conv_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    conv = db.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(404, "会话不存在")
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conv_id)
        .order_by(Message.id.asc())
        .all()
    )
    last_customer = next((m for m in reversed(msgs) if m.sender == "customer"), None)
    if not last_customer:
        raise HTTPException(400, "暂无客户问题可生成回复")
    history = [{"sender": m.sender, "content": m.content} for m in msgs]
    result = run_suggest(db, last_customer.content, history)
    return ok(AiSuggestOut(**result).model_dump())


@router.post("/conversations/{conv_id}/messages")
def send_message(
    conv_id: int,
    body: SendMessageIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = db.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(404, "会话不存在")
    if conv.status == "closed":
        raise HTTPException(400, "会话已结束")
    msg = Message(
        conversation_id=conv_id,
        sender="agent",
        content=body.content.strip(),
        is_ai_assisted=body.from_ai,
    )
    db.add(msg)
    conv.agent_id = user.id
    if conv.status == "queue":
        conv.status = "active"
    db.commit()
    db.refresh(msg)
    return ok(MessageOut.model_validate(msg).model_dump())


@router.post("/conversations/{conv_id}/close")
def close_conversation(
    conv_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    conv = db.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(404, "会话不存在")
    conv.status = "closed"
    db.add(
        Message(
            conversation_id=conv_id,
            sender="system",
            content="会话已由坐席结束",
        )
    )
    db.commit()
    return ok(_conv_out(db, conv))
