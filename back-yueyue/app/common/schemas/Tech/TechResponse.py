"""技术栈出参 VO。

ref_count = 被多少个项目引用:
  - 后台表格直接显示,删之前一眼看清牵连;
  - 弹窗里还能按它排序("用得多的排前面")。
name_key 不回传 —— 归一化是后端内部的事,前端只需要原样显示 name。
时间格式与 DiaryResponse 同款(空格分隔,前端 slice(0,16) 口径)。
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer


class TechResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    ref_count: int = 0
    created_at: datetime

    @field_serializer("created_at")
    def _fmt_time(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%d %H:%M:%S")
