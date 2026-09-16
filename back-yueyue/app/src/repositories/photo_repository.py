"""相册数据访问层(≈ Mapper):只把 SQL 变方法调用,不判权限不拼业务
(口径同 diary_repository,那层的三条原则原样成立)。

9/16 补全时修掉的初稿伤:
  - insert 返回 None → 返回刷新后的行(service 要拿 id/path 做展示和补偿删盘);
  - update 的 fields.pop("id") 空 dict 直接 KeyError → pop("id", None);
    且删掉"先 get、fields 为 None 又 get 一遍"的画蛇;
  - select_page 的 role 参数原来根本没被 service 透传(在 repo 这层默认 0 兜着,
    业务层形同虚设)—— 现在 role 老老实实从 service 传进来。
"""
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Photo


async def select_page(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    role: int = 0,
) -> tuple[int, list[Photo]]:
    skip = (page - 1) * page_size

    stmt = (
        select(Photo)
        .where(Photo.role == role)
        .order_by(Photo.id.desc())
        .offset(skip)
        .limit(page_size)
    )
    photos = (await db.execute(stmt)).scalars().all()

    total = await db.scalar(
        select(func.count()).select_from(Photo).where(Photo.role == role)
    )
    return total or 0, list(photos)


async def insert(db: AsyncSession, fields: dict[str, Any]) -> Photo:
    """fields 由 service 组装(过完校验的干净数据):type/name/role/path/size。"""
    photo = Photo(**fields)
    db.add(photo)
    await db.commit()
    await db.refresh(photo)  # 拿自增 id 和 server_default 的时间戳
    return photo


async def select_by_id(db: AsyncSession, photo_id: int) -> Photo | None:
    return await db.get(Photo, photo_id)


async def update(db: AsyncSession, photo_id: int, fields: dict) -> Photo | None:
    """fields 是 service 白名单过滤后的 {列名: 值},这里不再碰 DTO。"""
    photo = await db.get(Photo, photo_id)
    if photo is None:
        return None

    fields.pop("id", None)  # 防止 id 被改
    for key, value in fields.items():
        setattr(photo, key, value)

    await db.commit()
    await db.refresh(photo)
    return photo


async def delete(db: AsyncSession, photo_id: int) -> bool:
    photo = await db.get(Photo, photo_id)
    if photo is None:
        return False

    await db.delete(photo)
    await db.commit()
    return True
