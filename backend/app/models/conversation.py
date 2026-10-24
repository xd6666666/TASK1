from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# channels: wechat_mp | wecom | app | web
CHANNELS = ("wechat_mp", "wecom", "app", "web")
CHANNEL_LABELS = {
    "wechat_mp": "微信公众号",
    "wecom": "企业微信",
    "app": "App",
    "web": "Web 官网",
}


class Conversation(Base):
    __tablename__ = "conversation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"))
    channel: Mapped[str] = mapped_column(String(32), default="web")
    status: Mapped[str] = mapped_column(String(16), default="active")  # active|queue|closed
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("sys_user.id"), nullable=True)
    subject: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Message(Base):
    __tablename__ = "message"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversation.id"), index=True)
    sender: Mapped[str] = mapped_column(String(16))  # customer|agent|system
    content: Mapped[str] = mapped_column(Text)
    is_ai_assisted: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
