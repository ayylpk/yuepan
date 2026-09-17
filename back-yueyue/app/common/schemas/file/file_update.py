"""修改资料条目的入参 DTO:全部字段可选(PATCH 语义的 PUT,对齐 DiaryUpdate)。

能改的只有 name 和 role。9/17 原名上盘口径:**改 name = 磁盘文件同步改名**
(storage.rename_saved,撞名 400 不自动编号),type 会跟着新名字的扩展名走;
role 上锁/摆回公开不碰磁盘。真要换"内容"仍走删了重传。
"""
from typing import Annotated, Optional

from pydantic import BaseModel, Field


class FileUpdate(BaseModel):
    name: Optional[Annotated[str, Field(min_length=1, max_length=255)]] = None
    role: Optional[Annotated[int, Field(ge=0, le=1, description="0=公开 1=隐私")]] = None
