"""项目↔技术栈 全量重绑入参(PUT /api/projects/{id}/techs)。

语义 = 弹窗点"保存"后的最终列表:后端清旧绑定按 names 重建,
所以叫**全量替换**不是追加 —— 前端弹窗每次提交当前勾选+已手输的全部。
names 里的新名字照旧走大小写不敏感匹配,未建则建。
"""
from typing import Annotated

from pydantic import BaseModel, Field


class TechBind(BaseModel):
    names: list[Annotated[str, Field(max_length=50)]] = Field(
        default_factory=list, max_length=20, description="最终技术栈名列表(空=全解绑)"
    )
