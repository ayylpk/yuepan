"""新增技术栈入参(≈ @RequestBody + @Valid)。

name 用户手动填写(需求原话);大小写/首尾空格不用你操心,
service 统一 strip + 按 name_key 去重 —— "Vue"/"vue "/"VUE" 都会命中同一条,
不会插出三条。撞了不报错,幂等返回已有记录(弹窗"匹配"语义)。
"""
from typing import Annotated

from pydantic import BaseModel, Field


class TechCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=50, description="技术栈名,大小写不敏感")]
