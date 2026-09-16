"""改密入参:POST /api/auth/password(主密码)和 /api/auth/private/password(小屋)共用。

必带旧密码 = "改密不是覆盖,是换锁":先验你真的是你,再写新哈希。
min_length=6 和前端 SettingsView 的校验口径一致。
"""
from typing import Annotated

from pydantic import BaseModel, Field


class PasswordUpdate(BaseModel):
    old_password: Annotated[str, Field(min_length=1, max_length=128)]
    new_password: Annotated[str, Field(min_length=6, max_length=64)]
