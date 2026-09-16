"""新增日记的入参 DTO(Java 视角:@RequestBody + @Valid)。

pydantic 在进 Controller 前就把校验做完:字段非法直接 422,
service 层拿到的一定是干净数据,不用重复判。
"""
from typing import Annotated

from pydantic import BaseModel, Field


class DiaryCreate(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=120, description="标题")]
    content: str = Field(default="", description="正文,随便写")
    role: Annotated[int, Field(ge=0, le=1, description="0=正常公开 1=隐私(小屋)")] = 0
