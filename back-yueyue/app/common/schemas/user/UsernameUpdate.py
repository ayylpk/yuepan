"""改用户名入参:POST /api/auth/username(前端字段名是 new_username)。

也要带当前密码:改名属于敏感操作(用户名=登录凭证),防的是"会话没锁屏被人顺手改了名"。
"""
from typing import Annotated

from pydantic import BaseModel, Field


class UsernameUpdate(BaseModel):
    new_username: Annotated[str, Field(min_length=1, max_length=32)]
    password: Annotated[str, Field(min_length=1, max_length=128)]
