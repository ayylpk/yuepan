"""用户表数据访问(≈ UserMapper):只写查询,不碰业务。

9/16 随 diary 一起迁 SQLAlchemy async(≈ 从 JdbcTemplate 换 MyBatis):
原来手拼 SELECT 列名串 + ? 占位的写法由 ORM 表达式取代,
防注入口径不变 —— 值永远走绑定参数,列名永远来自代码白名单。
"""
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User


async def select_by_id(db: AsyncSession, user_id: int) -> User | None:
    return await db.get(User, user_id)


async def select_by_username(db: AsyncSession, username: str) -> User | None:
    stmt = select(User).where(User.username == username)
    return (await db.execute(stmt)).scalar_one_or_none()


async def update_fields(db: AsyncSession, user_id: int, fields: dict[str, Any]) -> None:
    """动态 SET(≈ MyBatis <set> + <if>):列名只来自 service 层白名单,值走绑定参数。"""
    if not fields:
        return
    user = await db.get(User, user_id)
    if user is None:
        return
    for column, value in fields.items():
        setattr(user, column, value)
    await db.commit()
    await db.refresh(user)
