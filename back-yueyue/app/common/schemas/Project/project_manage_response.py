"""管理端出参 VO:公开 ProjectResponse 的全部字段 + path。

为什么要单独一个 VO:
  - path 是本机目录(F:\\code\\...),公网 GET /api/projects 回传=泄露目录结构,
    所以公开 VO 故意不放;
  - 但后台"编辑项目"弹窗要回显 path 才能改,不能让人盲填;
  - 于是给登录用户单开 GET /api/projects/{id}/manage —— 多出来的只有 path,
    继承复用保证两个 VO 形状永远同步(公开字段加漏了这边会立刻发现)。
"""
from pydantic import Field

from app.common.schemas.project.project_response import ProjectResponse


class ProjectManageResponse(ProjectResponse):
    path: str = Field(default="", description="本机目录绝对路径(仅登录管理端可见)")
