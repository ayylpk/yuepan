"""小屋解锁入参:POST /api/auth/private/unlock。

只有密码一个字段 —— 验对了就把会话上的 private 标记点亮(见 tools/session.py),
锁芯本身存 user.private_password,和主密码是两把钥匙。
"""
from typing import Annotated

from pydantic import BaseModel, Field


class PrivateUnlock(BaseModel):
    password: Annotated[str, Field(min_length=1, max_length=128)]
