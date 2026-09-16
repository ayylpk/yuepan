from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import Photo


async def select_page(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    role: int = 0,
):
    skip = (page - 1)  * page_size
    stmt = (
        select(Photo)
        .where(Photo.role == role)
        .order_by(Photo.id.desc())
        .offset(skip)
        .limit(page_size)
    )

    result = await db.execute(stmt)
    photos = result.scalars().all()

    total = await db.scalar(
        select(func.count()).select_from(Photo).where(Photo.role == role)
    )

    return total,photos

async def insert(
    db: AsyncSession,
    type: str = "默认",
    path: str = "",
    role: int = 0,

)