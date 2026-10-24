from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class R(BaseModel, Generic[T]):
    code: int = 200
    msg: str = "success"
    data: T | None = None


def ok(data: Any = None, msg: str = "success") -> dict:
    return {"code": 200, "msg": msg, "data": data}


def fail(msg: str, code: int = 400) -> dict:
    return {"code": code, "msg": msg, "data": None}
