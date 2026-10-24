"""LangGraph agent: retrieve knowledge → draft customer-service reply."""

from __future__ import annotations

from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.rag.retriever import hybrid_retrieve


class AgentState(TypedDict):
    question: str
    history: list[dict]
    retrieved: list[dict]
    reply: str
    confidence: float
    mock: bool


def _llm():
    settings = get_settings()
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=0.4,
    )


def build_graph(db: Session):
    def retrieve_node(state: AgentState) -> AgentState:
        hits = hybrid_retrieve(db, state["question"], top_k=5)
        return {**state, "retrieved": hits}

    def draft_node(state: AgentState) -> AgentState:
        settings = get_settings()
        citations = state.get("retrieved") or []
        context = "\n\n".join(
            f"[{i+1}] {c.get('title', '')}\n{c.get('text', '')}" for i, c in enumerate(citations)
        )
        history_txt = "\n".join(
            f"{m.get('sender')}: {m.get('content')}" for m in (state.get("history") or [])[-8:]
        )
        confidence = 0.5
        if citations:
            confidence = min(0.98, 0.55 + 0.08 * len(citations) + 0.2 * float(citations[0].get("score", 0)))

        if settings.llm_mock:
            if citations:
                reply = (
                    f"根据知识库内容，建议回复如下：\n\n"
                    f"{citations[0].get('text', '')[:400]}\n\n"
                    f"（已参考 {len(citations)} 条知识，请人工确认后发送）"
                )
            else:
                reply = (
                    "暂未命中高相关知识。建议先安抚客户并确认订单号/商品信息，"
                    "必要时转售后专员跟进。（Mock 模式）"
                )
            return {**state, "reply": reply, "confidence": confidence, "mock": True}

        system = (
            "你是电商智能客服助手。根据检索到的知识与会话上下文，"
            "生成简洁、礼貌、可直接发送给客户的中文回复。"
            "不要编造政策；知识不足时明确说明需人工核实。"
            "回复中可自然提及关键信息，不要输出 Markdown 标题。"
        )
        user = (
            f"会话上下文:\n{history_txt or '无'}\n\n"
            f"客户最新问题:\n{state['question']}\n\n"
            f"检索知识:\n{context or '无'}\n\n"
            "请生成推荐回复："
        )
        try:
            llm = _llm()
            msg = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
            reply = str(msg.content).strip()
            return {**state, "reply": reply, "confidence": confidence, "mock": False}
        except Exception as exc:  # noqa: BLE001
            fallback = citations[0]["text"][:400] if citations else "暂时无法生成回复，请人工处理。"
            return {
                **state,
                "reply": f"{fallback}\n\n（模型调用失败，已回退：{exc}）",
                "confidence": max(0.4, confidence - 0.2),
                "mock": True,
            }

    graph = StateGraph(AgentState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("draft", draft_node)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "draft")
    graph.add_edge("draft", END)
    return graph.compile()


def run_suggest(db: Session, question: str, history: list[dict] | None = None) -> dict:
    app = build_graph(db)
    result = app.invoke(
        {
            "question": question,
            "history": history or [],
            "retrieved": [],
            "reply": "",
            "confidence": 0.0,
            "mock": True,
        }
    )
    citations = [
        {
            "title": c.get("title"),
            "score": round(float(c.get("score", 0)), 3),
            "source_type": c.get("source_type"),
            "source_id": c.get("source_id"),
            "snippet": (c.get("text") or "")[:160],
        }
        for c in result.get("retrieved") or []
    ]
    return {
        "reply": result.get("reply") or "",
        "confidence": round(float(result.get("confidence") or 0), 3),
        "citations": citations,
        "mock": bool(result.get("mock")),
    }
