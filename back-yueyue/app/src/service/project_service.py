"""项目业务层(≈ @Service):规则都在这 —— repository 只管取数,api 只管收发。

本模板示范的业务:
  1. VO 组装:project 行 + 技术栈 join 结果拼成前端契约的形状(description→desc);
  2. 技术栈匹配:创建/重绑都走 tech_service.resolve_names(大小写不敏感,未建则建);
  3. 删除三连:解绑 tech → files 索引置 NULL(散文件不陪葬)→ 删项目行;
  4. path 只进不出:能写进来(GET/响应 VO 里永远没有 path)。
"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas.project.project_create import ProjectCreate
from app.common.schemas.project.project_manage_response import ProjectManageResponse
from app.common.schemas.project.project_response import ProjectResponse
from app.common.schemas.project.project_update import ProjectUpdate
from app.common.schemas.project.tech_bind import TechBind
from app.database.models import Project
from app.src.repositories import code_repository, project_repository
from app.tools import storage
from app.src.service import tech_service

# 允许 PUT 修改的列白名单:不在表里的、不该动的(id/时间戳)都挡在这
UPDATABLE_FIELDS = {"name", "description", "code", "period", "path", "repo"}


def _to_response(project: Project, tech_names: list[str]) -> ProjectResponse:
    """DB 行 + join 出来的技术栈名 → 前端契约 VO。

    repo 回退规则(和 code 模块 select_by_repo_name 同一把尺):
    显式 repo 列优先,空则用 name —— 但没填 path 的項目不给 repo,
    免得前端"翻源码"按钮跳过去查不到树。
    """
    repo = None
    if project.path:
        repo = project.repo or project.name
    return ProjectResponse.model_validate(
        {
            "id": project.id,
            "name": project.name,
            "code": project.code,
            "desc": project.description,
            "tech": tech_names,
            "repo": repo,
            "period": project.period,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
        }
    )


async def _require_project(db: AsyncSession, project_id: int) -> Project:
    project = await project_repository.select_by_id(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


async def list_projects(db: AsyncSession) -> list[ProjectResponse]:
    """公开列表:项目行一次、绑定关系一次 join,拼好再回。"""
    projects = await project_repository.select_all(db)
    tech_map = await project_repository.select_tech_map(db)
    return [_to_response(p, tech_map.get(p.id, [])) for p in projects]


async def page_projects(db: AsyncSession, page: int, page_size: int):
    total, projects = await project_repository.select_page(db, page, page_size)
    tech_map = await project_repository.select_tech_map(db)
    return total, [_to_response(p, tech_map.get(p.id, [])) for p in projects]


async def get_project(db: AsyncSession, project_id: int) -> ProjectResponse:
    project = await _require_project(db, project_id)
    tech_map = await project_repository.select_tech_map(db)
    return _to_response(project, tech_map.get(project.id, []))


async def get_for_manage(db: AsyncSession, project_id: int) -> ProjectManageResponse:
    """管理弹窗回显:公开 VO 的全部字段 + path。

    鉴权在路由层(依赖 LoginUser),这里只管组装;path 只从这一条口子"出"。
    """
    project = await _require_project(db, project_id)
    tech_map = await project_repository.select_tech_map(db)
    base = _to_response(project, tech_map.get(project.id, []))
    return ProjectManageResponse.model_validate({**base.model_dump(), "path": project.path or ""})


async def create_project(db: AsyncSession, dto: ProjectCreate) -> ProjectResponse:
    if not dto.name.strip():
        raise HTTPException(status_code=400, detail="项目名不能为空")
    techs = await tech_service.resolve_names(db, dto.tech_names)
    project = await project_repository.insert(
        db,
        {
            "name": dto.name.strip(),
            "description": dto.description.strip(),
            "code": dto.code or "📦",
            "period": dto.period.strip(),
            # 入库前口径化:只留相对 REPOS_DIR 的路径(9/17 统一,绝对路径不再进 DB)
            "path": storage.normalize_repo_path(dto.path),
            "repo": dto.repo.strip(),
        },
    )
    if techs:
        await project_repository.replace_tech_links(db, project.id, [t.id for t in techs])
    return _to_response(project, [t.name for t in techs])


async def update_project(db: AsyncSession, project_id: int, dto: ProjectUpdate) -> ProjectResponse:
    project = await _require_project(db, project_id)
    dumped = dto.model_dump(exclude_unset=True)
    fields = {k: (v.strip() if isinstance(v, str) else v) for k, v in dumped.items() if k in UPDATABLE_FIELDS}
    if not fields:
        raise HTTPException(status_code=400, detail="没收到任何要修改的字段")
    if "name" in fields and not fields["name"]:
        raise HTTPException(status_code=400, detail="项目名不能为空")
    if "path" in fields:
        fields["path"] = storage.normalize_repo_path(fields["path"])
    project = await project_repository.update_fields(db, project, fields)
    tech_map = await project_repository.select_tech_map(db)
    return _to_response(project, tech_map.get(project.id, []))


async def delete_project(db: AsyncSession, project_id: int) -> None:
    project = await _require_project(db, project_id)
    # 三连:解绑 → 索引置空(散文件留着)→ 删行
    await project_repository.replace_tech_links(db, project.id, [])
    await code_repository.detach_project_files(db, project.id)
    await project_repository.delete(db, project)


async def bind_techs(db: AsyncSession, project_id: int, dto: TechBind) -> ProjectResponse:
    """弹窗保存:全量重绑。新名字自动建(大小写不敏感命中则复用)。"""
    project = await _require_project(db, project_id)
    techs = await tech_service.resolve_names(db, dto.names)
    await project_repository.replace_tech_links(db, project.id, [t.id for t in techs])
    return _to_response(project, [t.name for t in techs])
