"""修改相册条目的入参 DTO:全部字段可选(PATCH 语义的 PUT,对齐 DiaryUpdate)。

能改的只有元数据:type(换分类)/ role(上锁/摆回公开)。
name/size/path 与磁盘实体绑定,不开放修改(9/16 定稿:没有"盘上改名、库里改 path"
两条路径各改各的的漂移,改名这事真需要时再说)。
"""
from typing import Annotated, Optional

from pydantic import BaseModel, Field


class PhotoUpdate(BaseModel):
    type: Optional[Annotated[str, Field(max_length=20)]] = None
    role: Optional[Annotated[int, Field(ge=0, le=1, description="0=公开 1=隐私")]] = None
