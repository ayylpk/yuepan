"""相册输出 DTO(≈ VO)。

不回传 path:磁盘相对路径是后端内部事实,前端拿 id 拼 /api/photo/{id}/file 访问
(理由同 Project 不回传本机目录 —— 公网站点少暴露一寸结构是一寸)。
created_at 用 datetime + field_serializer 格式化成 "Y-m-d H:M:S" 字符串:
pydantic v2 的 str 字段不收 datetime(9/14 DiaryResponse 踩过,教训抄作业)。
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class PhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str = Field(description="相册/分类标签")
    name: str = Field(description="原始文件名(展示用)")
    role: int = Field(description="0=公开 1=隐私")
    size: int = Field(description="字节数")
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def _fmt_time(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%d %H:%M:%S")
