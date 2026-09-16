"""日记数据访问层(Repository,≈ MyBatis 的 Mapper + XML):
只干"把 SQL 变成方法调用"这一件事 —— 不校验、不判权限、不拼业务。

原则:
  1. 条件一律走 SQLAlchemy 表达式(等价 ? 占位),绝不拼字符串(SQL 注入的根防法);
  2. 返回 ORM 对象或 None,给 service 层随便加工;
  3. 这一层出现 if 判业务 = 写错了,回去找 service。

9/16 迁 async 时的三处修正:
  - select_by_id 忘了 return(恒 None,详情/改/删全 404);
  - update 的 db.get(id) 少传实体类,且签名收 DiaryUpdate 而 service 传的是
    过滤好的 dict —— 现在明确收 dict,DTO 语义留在 service 层;
  - 删掉 sqlite3 时代的 _COLUMNS/_to_dict 死代码(误导后人)。
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Diary


async def select_page(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    role: int = 0,
):
    skip = (page - 1) * page_size

    # 查当前页数据
    stmt = (
        select(Diary)
        .where(Diary.role == role)
        .order_by(Diary.id.desc())
        .offset(skip)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    diaries = result.scalars().all()

    # 查总数
    total = await db.scalar(
        select(func.count()).select_from(Diary).where(Diary.role == role)
    )

    return total, diaries


async def insert(
    db: AsyncSession,
    title: str,
    content: str,
    role: int = 0,
) -> Diary:
    diary = Diary(title=title, content=content, role=role)
    db.add(diary)
    await db.commit()
    await db.refresh(diary)   # 刷新,拿到数据库生成的 id、created_at
    return diary


async def select_by_id(
    db: AsyncSession,
    diary_id: int,
) -> Diary | None:
    """主键查询用 session.get 即可;没有命中的 get 本身就返回 None。"""
    return await db.get(Diary, diary_id)


async def update(
    db: AsyncSession,
    id: int,
    fields: dict,
) -> Diary | None:
    """fields 是 service 白名单过滤后的 {列名: 值},这里不再碰 DTO。"""
    diary = await db.get(Diary, id)
    if diary is None:
        return None

    fields.pop("id", None)  # 防止 id 被改
    for key, value in fields.items():
        setattr(diary, key, value)

    await db.commit()
    await db.refresh(diary)
    return diary


async def delete(
    db: AsyncSession,
    diary_id: int,
) -> bool:
    diary = await db.get(Diary, diary_id)
    if diary is None:
        return False

    await db.delete(diary)
    await db.commit()
    return True
