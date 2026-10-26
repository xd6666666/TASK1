from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.search_agent import run_search_answer
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import ok

router = APIRouter(prefix="/search", tags=["search"])


class SearchIn(BaseModel):
    query: str = Field(min_length=1)
    mode: str = "hybrid"  # hybrid|semantic|keyword
    threshold: float = 0.0
    top_k: int = 5
    feedback: str | None = None


@router.post("/query")
def search_query(
    body: SearchIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = run_search_answer(
        db,
        body.query,
        mode=body.mode if body.mode in ("hybrid", "semantic", "keyword") else "hybrid",
        threshold=body.threshold,
        top_k=body.top_k,
    )
    if body.feedback:
        result["feedback_received"] = body.feedback
    return ok(result)
