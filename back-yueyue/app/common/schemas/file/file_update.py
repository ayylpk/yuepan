"""修改资料条目的入参 DTO:全部字段可选(PATCH 语义的 PUT,对齐 DiaryUpdate)。

能改的只有 name(展示名)和 role(上锁/摆回公开)。
type 就是小写扩展名,跟着磁盘文件走,不单独开放改 —— 改了就和盘上真实文件不符,
真要换文件走"删了重传",一步到位不留漂移。
"""
from typing import Annotated, Optional

from pydantic import BaseModel, Field


class FileUpdate(BaseModel):
    name: Optional[Annotated[str, Field(min_length=1, max_length=255)]] = None
    role: Optional[Annotated[int, Field(ge=0, le=1, description="0=公开 1=隐私")]] = None
