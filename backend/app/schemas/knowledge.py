from datetime import datetime

from pydantic import BaseModel, Field


class FaqIn(BaseModel):
    question: str = Field(min_length=1, max_length=512)
    answer: str = Field(min_length=1)
    similar_questions: list[str] = Field(default_factory=list)
    category_id: int | None = None
    status: str = "published"


class FaqOut(BaseModel):
    id: int
    question: str
    answer: str
    similar_questions: list[str]
    category_id: int | None
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class DocOut(BaseModel):
    id: int
    title: str
    filename: str
    status: str
    chunk_count: int
    category_id: int | None
    summary: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ChunkOut(BaseModel):
    id: int
    chunk_index: int
    content: str

    model_config = {"from_attributes": True}


class CategoryOut(BaseModel):
    id: int
    name: str
    sort: int

    model_config = {"from_attributes": True}
