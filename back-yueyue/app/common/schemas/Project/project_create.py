"""新增项目入参 DTO(≈ @RequestBody + @Valid)。

tech_names 是"弹窗匹配"的入口:手输 + 弹窗选出来的名字都从这进,
service 逐个按大小写不敏感匹配(tech_service.resolve_names):
命中已有 → 直接绑;没命中 → 自动建一条再绑。空列表=不带技术栈。
"""
from typing import Annotated, Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100, description="项目名")]
    description: Annotated[str, Field(max_length=2000)] = ""
    code: Annotated[str, Field(max_length=8)] = "📦"  # emoji 占位图标
    period: Annotated[str, Field(max_length=40)] = ""
    path: Annotated[str, Field(max_length=260)] = ""  # 本机目录;非空才进 /api/code/repos
    repo: Annotated[str, Field(max_length=100)] = ""  # 仓库名,空则按 name 匹配
    tech_names: list[Annotated[str, Field(max_length=50)]] = Field(
        default_factory=list, max_length=20, description="技术栈名(可含新名字,自动创建)"
    )
