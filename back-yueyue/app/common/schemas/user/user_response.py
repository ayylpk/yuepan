"""出参(≈ 给前端的 VO):只放能看的字段。

password 故意不在这里 —— 库行里带着哈希,service 在 model_validate 前
把它 pop 掉;就算忘了 pop,pydantic 默认也会把 schema 外的字段丢掉,
双保险,哈希永远出不了后端。
比原稿多了 id:前端拿 id 才能定位改谁(单用户站也是主键,别裸 username)。
"""
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: int
    username: str
    email: Annotated[str, Field(default="")]
    phone: Annotated[str, Field(default="")]
    QQ: Annotated[str, Field(default="")]
    created_at: datetime
