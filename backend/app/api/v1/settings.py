from __future__ import annotations

import json

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.qa import SysSetting
from app.models.user import User
from app.schemas.common import ok

router = APIRouter(prefix="/settings", tags=["settings"])

DEFAULTS = {
    "ai": {
        "profile": "pro",
        "temperature": 0.4,
        "show_citations": True,
        "llm_mock": True,
    },
    "channels": [
        {"key": "web", "name": "网页在线客服", "enabled": True, "status": "connected"},
        {"key": "wechat_mp", "name": "微信公众号", "enabled": True, "status": "connected"},
        {"key": "wecom", "name": "企业微信", "enabled": True, "status": "connected"},
        {"key": "app", "name": "APP 内嵌客服", "enabled": True, "status": "connected"},
        {"key": "phone", "name": "400 电话热线", "enabled": False, "status": "unconfigured"},
        {"key": "email", "name": "邮件工单", "enabled": True, "status": "connected"},
    ],
    "qa_notify": {
        "auto_inspect": True,
        "high_risk_alert": True,
        "daily_report": True,
        "sample_ratio": 25,
        "low_score_review": True,
        "low_score_threshold": 80,
    },
    "team": {
        "agents": 12,
        "online": 8,
        "busy": 2,
        "qa_staff": 3,
        "kb_ops": 2,
        "retention_days": 180,
    },
}


def _get_json(db: Session, key: str, default):
    row = db.query(SysSetting).filter(SysSetting.key == key).first()
    if not row:
        return default
    try:
        return json.loads(row.value)
    except json.JSONDecodeError:
        return default


def _set_json(db: Session, key: str, value) -> None:
    row = db.query(SysSetting).filter(SysSetting.key == key).first()
    raw = json.dumps(value, ensure_ascii=False)
    if row:
        row.value = raw
    else:
        db.add(SysSetting(key=key, value=raw))
    db.commit()


class SettingsIn(BaseModel):
    ai: dict | None = None
    channels: list | None = None
    qa_notify: dict | None = None
    team: dict | None = None


@router.get("")
def get_all(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    conf = get_settings()
    ai = _get_json(db, "ai", DEFAULTS["ai"])
    ai["llm_mock"] = conf.llm_mock
    ai["llm_model"] = conf.llm_model
    ai["llm_base_url"] = conf.llm_base_url
    return ok(
        {
            "ai": ai,
            "channels": _get_json(db, "channels", DEFAULTS["channels"]),
            "qa_notify": _get_json(db, "qa_notify", DEFAULTS["qa_notify"]),
            "team": _get_json(db, "team", DEFAULTS["team"]),
        }
    )


@router.put("")
def save_all(
    body: SettingsIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.ai is not None:
        _set_json(db, "ai", body.ai)
    if body.channels is not None:
        _set_json(db, "channels", body.channels)
    if body.qa_notify is not None:
        _set_json(db, "qa_notify", body.qa_notify)
    if body.team is not None:
        _set_json(db, "team", body.team)
    conf = get_settings()
    ai = _get_json(db, "ai", DEFAULTS["ai"])
    ai["llm_mock"] = conf.llm_mock
    ai["llm_model"] = conf.llm_model
    ai["llm_base_url"] = conf.llm_base_url
    return ok(
        {
            "ai": ai,
            "channels": _get_json(db, "channels", DEFAULTS["channels"]),
            "qa_notify": _get_json(db, "qa_notify", DEFAULTS["qa_notify"]),
            "team": _get_json(db, "team", DEFAULTS["team"]),
        }
    )


@router.get("/model/health")
def model_health(_: User = Depends(get_current_user)):
    conf = get_settings()
    if conf.llm_mock:
        return ok({"ok": True, "mode": "mock", "detail": "当前为 Mock 模式，未探测真实节点"})
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{conf.llm_base_url.rstrip('/')}/models", headers={
                "Authorization": f"Bearer {conf.llm_api_key}"
            })
            ok_flag = resp.status_code < 500
            return ok(
                {
                    "ok": ok_flag,
                    "mode": "live",
                    "status_code": resp.status_code,
                    "detail": resp.text[:200],
                }
            )
    except Exception as exc:  # noqa: BLE001
        return ok({"ok": False, "mode": "live", "detail": str(exc)})
