"""日记出参 DTO(Java 视角:VO)。

DAO 返回的 ORM 对象会被 Result/PageResult 的 response_model 按这个形状过滤,
以后表里加了不想暴露的列(比如内部标记),这里不写就自动不出接口。

9/16 迁 SQLAlchemy 后时间列拿回来是 datetime,而 pydantic v2 的 str 字段
**不接** datetime(v1 会帮你 str(),v2 直接校验炸)。类型改回 datetime,
再用 field_serializer 统一吐 "YYYY-MM-DD HH:MM:SS" —— 前端
created_at.slice(0, 16) 的展示口径不变(ISO 的 T 分隔会被切进去)。
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class DiaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str = Field(description="正文")
    role: int
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def _fmt_time(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%d %H:%M:%S")
