"""项目数据访问层(≈ ProjectMapper):只查数,匹配/白名单规则在 service。"""
from typing import Any

# sa_delete 加前缀:本模块自己也有个 delete(),直接 import delete 会被遮住
# (9/16 冒烟实测炸过:TypeError: delete() missing 1 required positional argument)
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Project, ProjectTech, TechStack


async def select_all(db: AsyncSession) -> list[Project]:
    stmt = select(Project).order_by(Project.id.desc())
    return list((await db.execute(stmt)).scalars().all())


async def select_page(db: AsyncSession, page: int, page_size: int):
    skip = (page - 1) * page_size
    stmt = select(Project).order_by(Project.id.desc()).offset(skip).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()
    total = await db.scalar(select(func.count()).select_from(Project))
    return total or 0, list(rows)


async def select_by_id(db: AsyncSession, project_id: int) -> Project | None:
    return await db.get(Project, project_id)


async def select_by_repo_name(db: AsyncSession, repo: str) -> Project | None:
    """代码模块专用:/api/code/* 的 repo 参数 → 项目行。
    repo 列优先,空则按 name 兜底(与 ProjectResponse.repo 的回退规则同一把尺)。
    """
    stmt = select(Project).where(
        (Project.repo == repo) | ((Project.repo == "") & (Project.name == repo))
    )
    return (await db.execute(stmt)).scalars().first()


async def select_all_with_path(db: AsyncSession) -> list[Project]:
    """/api/code/repos 数据源:path 非空才进白名单。"""
    stmt = select(Project).where(Project.path != "").order_by(Project.id.desc())
    return list((await db.execute(stmt)).scalars().all())


async def insert(db: AsyncSession, fields: dict[str, Any]) -> Project:
    project = Project(**fields)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def update_fields(db: AsyncSession, project: Project, fields: dict[str, Any]) -> Project:
    """project 是 service 判过存在的 ORM 行;列名来自白名单,值走绑定参数。"""
    for column, value in fields.items():
        setattr(project, column, value)
    await db.commit()
    await db.refresh(project)
    return project


async def delete(db: AsyncSession, project: Project) -> None:
    await db.delete(project)
    await db.commit()


# ---------- 技术栈绑定(多对多) ----------

async def select_tech_map(db: AsyncSession) -> dict[int, list[str]]:
    """一次 join 拿全部 {project_id: [技术栈展示名]} —— 列表页防 N+1 的写法。

    按 tech_stack.id 排序,项目卡片上的技术栈顺序稳定(先建的在前)。
    """
    stmt = (
        select(ProjectTech.project_id, TechStack.name)
        .join(TechStack, TechStack.id == ProjectTech.tech_id)
        .order_by(TechStack.id)
    )
    result: dict[int, list[str]] = {}
    for project_id, name in (await db.execute(stmt)).all():
        result.setdefault(project_id, []).append(name)
    return result


async def replace_tech_links(db: AsyncSession, project_id: int, tech_ids: list[int]) -> None:
    """全量重绑:删该项目的旧行、插新行,一次 commit(≈ <delete> + <insert> 同事务)。"""
    await db.execute(sa_delete(ProjectTech).where(ProjectTech.project_id == project_id))
    for tech_id in tech_ids:
        db.add(ProjectTech(project_id=project_id, tech_id=tech_id))
    await db.commit()
