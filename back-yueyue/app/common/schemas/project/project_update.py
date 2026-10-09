"""改项目入参 DTO(PATCH 语义,同 DiaryUpdate 口径)。

不传=不动;传空串 path="" 是合法动作 = 摘掉本机目录(该项目的代码树随之消失)。
tech 不走这里:改绑是独立动作,走 PUT /api/projects/{id}/techs(弹窗"保存") ——
分开的好处:改个简介不会把技术栈列表悄悄覆盖回去,两个意图各管各的。
"""
from typing import Annotated, Optional

from pydantic import BaseModel, Field


class ProjectUpdate(BaseModel):
    name: Optional[Annotated[str, Field(min_length=1, max_length=100)]] = None
    description: Optional[Annotated[str, Field(max_length=2000)]] = None
    code: Optional[Annotated[str, Field(max_length=8)]] = None
    period: Optional[Annotated[str, Field(max_length=40)]] = None
    path: Optional[Annotated[str, Field(max_length=260)]] = None
    repo: Optional[Annotated[str, Field(max_length=100)]] = None
