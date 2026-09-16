"""项目出参 DTO(Java 视角:VO)。形状逐字对齐前端 src/api/types.ts 的 Project 接口。

字段口径:
  - desc 是 DB 列 description 的映射(service 层组 dict 时改名),VO 迁就前端而不是反过来;
  - tech 不在 project 表里(在 tech_stack + project_tech 关联表),
    由 service 一次 join 查完塞进来 —— 这里只声明形状;
  - repo:后端规则 = path 非空时返回 repo(空则回退 name),path 为空返回 None,
    前端 ProjectsView 拿它决定"翻源码"按钮显不显示,点了带 ?repo= 跳 CodeView;
  - ⚠️ path 故意不进本 VO:站点在公网,回传 F:\\code\\... 等于泄露本机目录结构。
    管理弹窗要显示/修改 path 走 GET /api/projects/{id}/manage(登录),或留空占位。
  - 时间序列化与 DiaryResponse 同款(空格分隔,前端 slice(0,16) 口径)。
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str = Field(default="📦", description="emoji 占位图标")
    desc: str = Field(default="", description="简介,DB 列叫 description")
    tech: list[str] = Field(default_factory=list, description="技术栈展示名,关联表 join")
    repo: Optional[str] = Field(default=None, description="代码白名单仓库名;null=没挂代码")
    period: str = Field(default="", description="时间段,手填任意口径")
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def _fmt_time(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%d %H:%M:%S")
