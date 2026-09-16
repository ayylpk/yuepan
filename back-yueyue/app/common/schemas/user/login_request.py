"""登录入参:POST /api/auth/login 的请求体(前端 stores/auth.ts login())。

字段名和前端 JSON 一字不差 —— 这是契约,改这边就得改那边。
"""
from typing import Annotated

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: Annotated[str, Field(min_length=1, max_length=32)]
    # 登录不设 min_length:校验"对不对"交给哈希比对,格式规矩只属于设置新密码时
    password: Annotated[str, Field(min_length=1, max_length=128)]
