"""技术栈数据访问层(≈ TechMapper):只查数,大小写规则在 service 归一化后才到这。"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import ProjectTech, TechStack


async def select_by_key(db: AsyncSession, name_key: str) -> TechStack | None:
    """按归一化键找 —— 大小写不敏感的"查"就靠它(唯一索引,快)。"""
    stmt = select(TechStack).where(TechStack.name_key == name_key)
    return (await db.execute(stmt)).scalar_one_or_none()


async def insert(db: AsyncSession, name: str, name_key: str) -> TechStack:
    tech = TechStack(name=name, name_key=name_key)
    db.add(tech)
    await db.commit()
    await db.refresh(tech)
    return tech


async def select_by_id(db: AsyncSession, tech_id: int) -> TechStack | None:
    return await db.get(TechStack, tech_id)


async def count_refs(db: AsyncSession, tech_id: int) -> int:
    stmt = select(func.count()).select_from(ProjectTech).where(ProjectTech.tech_id == tech_id)
    return await db.scalar(stmt) or 0


async def select_list(
    db: AsyncSession,
    keyword: str | None = None,
    page: int | None = None,
    page_size: int = 10,
):
    """查列表(带 ref_count),/list 全量和 /page 分页共用这一条。

    keyword 按 name_key 模糊匹配(传入前 service 已把关键词归一化成小写),
    所以 "vu" 能搜到 "Vue" —— 查询侧的大小写不敏感是白捡的。
    page=None 不分页(弹窗数据源,字典表量小)。
    返回 [(TechStack, ref_count), ...]。
    """
    stmt = (
        select(TechStack, func.count(ProjectTech.tech_id).label("ref_count"))
        .outerjoin(ProjectTech, ProjectTech.tech_id == TechStack.id)
        .group_by(TechStack.id)
        .order_by(TechStack.id.desc())
    )
    if keyword:
        stmt = stmt.where(TechStack.name_key.contains(keyword))
    if page is not None:
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


async def count_all(db: AsyncSession, keyword: str | None = None) -> int:
    stmt = select(func.count()).select_from(TechStack)
    if keyword:
        stmt = stmt.where(TechStack.name_key.contains(keyword))
    return await db.scalar(stmt) or 0


async def delete(db: AsyncSession, tech: TechStack) -> None:
    await db.delete(tech)
    await db.commit()


async def delete_links_by_tech(db: AsyncSession, tech_id: int) -> None:
    """删 tech 前清它与项目的绑定(service 判完引用数才会走到这)。"""
    stmt = select(ProjectTech).where(ProjectTech.tech_id == tech_id)
    for link in (await db.execute(stmt)).scalars().all():
        await db.delete(link)
    await db.commit()
