"""LangGraph: retrieve → synthesize aggregated answer for knowledge search page."""

from __future__ import annotations

from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.rag.retriever import retrieve


class State(TypedDict):
    question: str
    mode: str
    threshold: float
    top_k: int
    items: list[dict]
    stats: dict
    answer: str
    mock: bool


def _llm():
    s = get_settings()
    return ChatOpenAI(
        base_url=s.llm_base_url,
        api_key=s.llm_api_key,
        model=s.llm_model,
        temperature=0.3,
    )


def run_search_answer(
    db: Session,
    question: str,
    mode: str = "hybrid",
    threshold: float = 0.0,
    top_k: int = 5,
) -> dict:
    def retrieve_node(state: State) -> State:
        pack = retrieve(
            db,
            state["question"],
            mode=state["mode"],
            top_k=state["top_k"],
            threshold=state["threshold"],
        )
        return {**state, "items": pack["items"], "stats": pack["stats"]}

    def answer_node(state: State) -> State:
        settings = get_settings()
        items = state.get("items") or []
        ctx = "\n\n".join(
            f"[{i+1}] {x.get('title')}\n{x.get('text')}" for i, x in enumerate(items)
        )
        if settings.llm_mock:
            if items:
                text = items[0].get("text") or ""
                answer = (
                    f"根据检索结果，建议答复：\n\n{text[:500]}\n\n"
                    f"（共召回 {len(items)} 条，Mock 聚合）"
                )
            else:
                answer = "未召回到相关知识，建议补充 FAQ 或文档后再试。"
            return {**state, "answer": answer, "mock": True}
        try:
            llm = _llm()
            msg = llm.invoke(
                [
                    SystemMessage(
                        content=(
                            "你是知识库问答助手。基于检索片段生成简洁中文答案，"
                            "标注关键信息，不要编造政策。"
                        )
                    ),
                    HumanMessage(
                        content=f"问题：{state['question']}\n\n检索：\n{ctx or '无'}\n\n请给出聚合答案："
                    ),
                ]
            )
            return {**state, "answer": str(msg.content).strip(), "mock": False}
        except Exception as exc:  # noqa: BLE001
            fallback = (items[0]["text"][:400] if items else "暂无答案") + f"\n（模型失败：{exc}）"
            return {**state, "answer": fallback, "mock": True}

    g = StateGraph(State)
    g.add_node("retrieve", retrieve_node)
    g.add_node("answer", answer_node)
    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "answer")
    g.add_edge("answer", END)
    result = g.compile().invoke(
        {
            "question": question,
            "mode": mode,
            "threshold": threshold,
            "top_k": top_k,
            "items": [],
            "stats": {},
            "answer": "",
            "mock": True,
        }
    )
    return {
        "answer": result.get("answer") or "",
        "items": result.get("items") or [],
        "stats": result.get("stats") or {},
        "mock": bool(result.get("mock")),
        "citations": [
            {
                "title": x.get("title"),
                "score": round(float(x.get("score", 0)), 3),
                "source_type": x.get("source_type"),
                "via": x.get("via"),
            }
            for x in (result.get("items") or [])
        ],
    }
