"""修改资料入参(≈ DiaryUpdate 同款 PATCH 语义)。

规则:哪个字段要改传哪个,不传(=None)保持原样 —— 所以默认必须是 None,
不能像原稿那样拿 "admin"/"123456" 当默认值(那等于"不动也给你改成 admin")。

password 不在这里:改密码必须走 /api/auth/password(先验旧密码),
否则这个 PUT 就成了"知道 id 就能顶号"的后门。
"""
from typing import Annotated, Optional

from pydantic import BaseModel, Field


class UserUpdate(BaseModel):
    username: Optional[Annotated[str, Field(min_length=1, max_length=32)]] = None
    email: Optional[Annotated[str, Field(max_length=64)]] = None
    phone: Optional[Annotated[str, Field(max_length=32)]] = None
    QQ: Optional[Annotated[str, Field(max_length=32)]] = None
