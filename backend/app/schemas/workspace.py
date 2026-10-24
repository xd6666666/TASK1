from datetime import datetime

from pydantic import BaseModel, Field


class MessageOut(BaseModel):
    id: int
    sender: str
    content: str
    is_ai_assisted: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: int
    session_no: str
    channel: str
    channel_label: str
    status: str
    subject: str
    customer_id: int
    customer_name: str
    customer_level: str
    customer_phone: str
    customer_tags: str
    last_message: str = ""
    updated_at: datetime | None = None
    created_at: datetime | None = None


class SendMessageIn(BaseModel):
    content: str = Field(min_length=1)
    from_ai: bool = False


class AiSuggestOut(BaseModel):
    reply: str
    confidence: float
    citations: list[dict]
    mock: bool = False
