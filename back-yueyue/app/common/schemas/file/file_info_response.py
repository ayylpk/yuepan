"""资料库输出 DTO(≈ VO)。

类名不叫 FileResponse:fastapi.responses.FileResponse(下载应答)会和它在
api/file.py 同框打架,多两个 Info 字换一世太平。
口径同 PhotoResponse:path(相对 resources/ 的磁盘路径)不回传前端。
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class FileInfoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str = Field(description="原始文件名(展示+下载名)")
    type: str = Field(description="小写扩展名,不带点")
    role: int = Field(description="0=公开 1=隐私")
    size: int = Field(description="字节数")
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def _fmt_time(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%d %H:%M:%S")
