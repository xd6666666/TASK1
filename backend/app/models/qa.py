from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class QaRule(Base):
    __tablename__ = "qa_rule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    group_name: Mapped[str] = mapped_column(String(64), default="服务规范")
    description: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(16), default="medium")  # low|medium|high
    enabled: Mapped[bool] = mapped_column(default=True)
    check_prompt: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class QaResult(Base):
    __tablename__ = "qa_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversation.id"), index=True)
    score: Mapped[float] = mapped_column(Float, default=100.0)
    level: Mapped[str] = mapped_column(String(16), default="pass")  # pass|review|risk
    hit_rules: Mapped[str] = mapped_column(Text, default="[]")  # JSON list of rule names
    summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="done")  # done|pending_review|resolved
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("sys_user.id"), nullable=True)
    review_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Alert(Base):
    __tablename__ = "alert"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[str] = mapped_column(String(16), default="warn")  # danger|warn|ok
    title: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str] = mapped_column(String(255), default="")
    link_page: Mapped[str] = mapped_column(String(64), default="")
    handled: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SysSetting(Base):
    __tablename__ = "sys_setting"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text, default="{}")
