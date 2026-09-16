from typing import Optional
from pydantic import BaseModel


class Result[T](BaseModel):
    code: int = 200
    message: str = "success"
    data: Optional[T] = None

    @classmethod
    def success(cls, data: Optional[T] = None, message: str = "success") -> "Result[T]":
        return cls(code=200, message=message, data=data)

    @classmethod
    def fail(cls, message: str = "error", code: int = 500) -> "Result[T]":
        return cls(code=code, message=message, data=None)