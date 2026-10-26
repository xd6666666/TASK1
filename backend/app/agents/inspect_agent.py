"""LangGraph QA inspect: score conversation against enabled rules."""

from __future__ import annotations

import json
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.conversation import Message
from app.models.qa import QaResult, QaRule


class State(TypedDict):
    conversation_id: int
    transcript: str
    rules: list[dict]
    score: float
    hit_rules: list[str]
    level: str
    summary: str
    mock: bool


def _llm():
    s = get_settings()
    return ChatOpenAI(
        base_url=s.llm_base_url,
        api_key=s.llm_api_key,
        model=s.llm_model,
        temperature=0.1,
    )


def inspect_conversation(db: Session, conversation_id: int) -> QaResult:
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.id.asc())
        .all()
    )
    transcript = "\n".join(f"{m.sender}: {m.content}" for m in msgs)
    rules = db.query(QaRule).filter(QaRule.enabled.is_(True)).all()
    rule_dicts = [
        {
            "id": r.id,
            "name": r.name,
            "severity": r.severity,
            "description": r.description,
            "check_prompt": r.check_prompt,
        }
        for r in rules
    ]

    def analyze(state: State) -> State:
        settings = get_settings()
        hits: list[str] = []
        score = 100.0
        summary = "质检通过"
        # heuristic baseline
        text = state["transcript"].lower()
        for r in state["rules"]:
            keywords = []
            if "辱骂" in r["name"] or "态度" in r["name"]:
                keywords = ["滚", "白痴", "傻"]
            if "超时" in r["name"]:
                keywords = []
            if "隐私" in r["name"]:
                keywords = ["身份证号", "完整银行卡"]
            if any(k and k in state["transcript"] for k in keywords):
                hits.append(r["name"])
                score -= 25 if r["severity"] == "high" else 12

            # soft checks from description/prompt keywords in Chinese mock
            tip = (r.get("check_prompt") or "") + (r.get("description") or "")
            if "必须致歉" in tip and "抱歉" not in state["transcript"] and "对不起" not in state["transcript"]:
                if "致歉" in r["name"] or "安抚" in r["name"]:
                    hits.append(r["name"])
                    score -= 10

        if not settings.llm_mock and state["rules"]:
            try:
                llm = _llm()
                prompt = (
                    f"会话内容：\n{state['transcript']}\n\n"
                    f"规则：\n{json.dumps(state['rules'], ensure_ascii=False)}\n\n"
                    "请输出 JSON：{\"score\":0-100,\"hit_rules\":[规则名],\"summary\":\"一句话\"}"
                )
                msg = llm.invoke(
                    [
                        SystemMessage(content="你是客服质检员，只输出 JSON。"),
                        HumanMessage(content=prompt),
                    ]
                )
                raw = str(msg.content)
                start = raw.find("{")
                end = raw.rfind("}")
                if start >= 0 and end > start:
                    data = json.loads(raw[start : end + 1])
                    score = float(data.get("score", score))
                    hits = list(data.get("hit_rules") or hits)
                    summary = str(data.get("summary") or summary)
                    return {
                        **state,
                        "score": score,
                        "hit_rules": hits,
                        "level": "risk" if score < 70 else ("review" if score < 85 else "pass"),
                        "summary": summary,
                        "mock": False,
                    }
            except Exception:
                pass

        score = max(0.0, min(100.0, score))
        if not hits:
            summary = "未命中违规规则"
        else:
            summary = f"命中规则：{'、'.join(hits)}"
        level = "risk" if score < 70 else ("review" if score < 85 or hits else "pass")
        if hits and level == "pass":
            level = "review"
        return {
            **state,
            "score": score,
            "hit_rules": hits,
            "level": level,
            "summary": summary,
            "mock": True,
        }

    g = StateGraph(State)
    g.add_node("analyze", analyze)
    g.add_edge(START, "analyze")
    g.add_edge("analyze", END)
    result = g.compile().invoke(
        {
            "conversation_id": conversation_id,
            "transcript": transcript or "(空会话)",
            "rules": rule_dicts,
            "score": 100.0,
            "hit_rules": [],
            "level": "pass",
            "summary": "",
            "mock": True,
        }
    )

    status = "pending_review" if result["level"] in ("review", "risk") else "done"
    row = QaResult(
        conversation_id=conversation_id,
        score=float(result["score"]),
        level=result["level"],
        hit_rules=json.dumps(result["hit_rules"], ensure_ascii=False),
        summary=result["summary"],
        status=status,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
