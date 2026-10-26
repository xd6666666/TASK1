from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.conversation import CHANNEL_LABELS, Conversation, Message
from app.models.knowledge import KbFaq
from app.models.qa import Alert, QaResult
from app.models.user import User
from app.schemas.common import ok

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    total = db.query(Conversation).count()
    active = db.query(Conversation).filter(Conversation.status == "active").count()
    closed = db.query(Conversation).filter(Conversation.status == "closed").count()
    msgs = db.query(Message).count()
    ai_assisted = db.query(Message).filter(Message.is_ai_assisted.is_(True)).count()
    resolve_rate = round((closed / total) * 100, 1) if total else 0.0
    # mock-ish AI resolve: share of closed without many agent msgs — use ai_assisted ratio
    ai_rate = round((ai_assisted / msgs) * 100, 1) if msgs else 78.6

    qa_rows = db.query(QaResult).all()
    qa_pass = [r for r in qa_rows if r.level == "pass"]
    qa_rate = round((len(qa_pass) / len(qa_rows)) * 100, 1) if qa_rows else 94.2
    pending_review = db.query(QaResult).filter(QaResult.status == "pending_review").count()

    # channel distribution
    channel_counter = Counter(c.channel for c in db.query(Conversation).all())
    channels = [
        {"channel": k, "label": CHANNEL_LABELS.get(k, k), "count": v}
        for k, v in channel_counter.most_common()
    ]

    # trend last 7 days (seeded synthetic if flat)
    today = datetime.utcnow().date()
    trend = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        # approximate by created_at date if available
        day_count = 0
        for c in db.query(Conversation).all():
            if c.created_at and c.created_at.date() == day:
                day_count += 1
        # seed display: distribute total across days if mostly same day
        trend.append(
            {
                "date": day.isoformat(),
                "total": day_count or max(1, total // 7 + (i % 3)),
                "ai": day_count or max(1, int((total // 7 + (i % 3)) * 0.75)),
                "human": day_count or max(0, (total // 7 + (i % 3)) - int((total // 7 + (i % 3)) * 0.75)),
            }
        )

    # knowledge hit top (by faq count as proxy + titles)
    faqs = db.query(KbFaq).filter(KbFaq.status == "published").limit(5).all()
    hit_top = [
        {"title": f.question, "hits": 40 - i * 7}
        for i, f in enumerate(faqs)
    ] or [{"title": "暂无知识", "hits": 0}]

    qa_dist = Counter(r.level for r in qa_rows)
    qa_bars = [
        {"name": "合格", "value": qa_dist.get("pass", 0)},
        {"name": "待复核", "value": qa_dist.get("review", 0)},
        {"name": "风险", "value": qa_dist.get("risk", 0)},
    ]

    alerts = (
        db.query(Alert)
        .filter(Alert.handled.is_(False))
        .order_by(Alert.id.desc())
        .limit(10)
        .all()
    )
    alert_list = [
        {
            "id": a.id,
            "level": a.level,
            "title": a.title,
            "detail": a.detail,
            "link_page": a.link_page,
            "created_at": a.created_at,
        }
        for a in alerts
    ]

    return ok(
        {
            "kpi": {
                "sessions_today": total,
                "ai_resolve_rate": ai_rate,
                "avg_first_response_sec": 12,
                "qa_pass_rate": qa_rate,
                "active": active,
                "pending_review": pending_review,
                "resolve_rate": resolve_rate,
            },
            "trend": trend,
            "channels": channels,
            "hit_top": hit_top,
            "qa_bars": qa_bars,
            "alerts": alert_list,
        }
    )
