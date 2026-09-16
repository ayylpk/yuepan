"""资料库数据访问层(≈ Mapper):口径同 photo_repository,五件事一件不多。

select_page / insert(返回刷新行)/ select_by_id / update(白名单 dict)/ delete。
"""
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import File


async def select_page(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    role: int = 0,
) -> tuple[int, list[File]]:
    skip = (page - 1) * page_size

    stmt = (
        select(File)
        .where(File.role == role)
        .order_by(File.id.desc())
        .offset(skip)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).scalars().all()

    total = await db.scalar(
        select(func.count()).select_from(File).where(File.role == role)
    )
    return total or 0, list(rows)


async def insert(db: AsyncSession, fields: dict[str, Any]) -> File:
    """fields 由 service 组装(过完校验的干净数据):name/type/role/path/size。"""
    item = File(**fields)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def select_by_id(db: AsyncSession, file_id: int) -> File | None:
    return await db.get(File, file_id)


async def update(db: AsyncSession, file_id: int, fields: dict) -> File | None:
    """fields 是 service 白名单过滤后的 {列名: 值},这里不再碰 DTO。"""
    item = await db.get(File, file_id)
    if item is None:
        return None

    fields.pop("id", None)
    for key, value in fields.items():
        setattr(item, key, value)

    await db.commit()
    await db.refresh(item)
    return item


async def delete(db: AsyncSession, file_id: int) -> bool:
    item = await db.get(File, file_id)
    if item is None:
        return False

    await db.delete(item)
    await db.commit()
    return True
