from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar('T')


class PageResult(BaseModel, Generic[T]):
    count: int = 0
    data: list[T] = []

    @classmethod
    def success(
        cls,
        data: Optional[list[T]] = None,
        count: Optional[int] = None,
    ) -> "PageResult[T]":
        data = data or []
        return cls(count=count if count is not None else len(data), data=data)