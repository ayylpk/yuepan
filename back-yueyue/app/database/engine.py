"""连接与会话(Java 视角:DataSource + SqlSessionFactory + @Transactional 边界)。

9/16 结构整理:原来 database/db.py 一个文件既配连接又画表,和 tools/db.py 撞名,
拆成三包 —— engine.py(本文件:连接/会话)、models.py(实体)、bootstrap.py(启动动作)。

SQLite 铁律别忘:
  - URL 必须显式写 +aiosqlite 驱动,create_async_engine 不会替你自动换
    (9/16 实测:自动换驱动的说法是错的,pysqlite 直接报 "requires an async driver");
  - engine 建之前先 mkdir 库文件父目录,SQLite 不替你建目录,首连就是
    "unable to open database file"。
"""
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.common.config.settings import RESOURCES_DIR

# 库文件搬进顶层 resources/database/(与 photo/file 同一家);
# 旧位置 app/database/resources/database/ 已废弃删除,免得再长出第二个真相源。
DB_PATH: Path = RESOURCES_DIR / "database" / "yueyue.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}")


class Base(DeclarativeBase):
    pass


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """请求级 session(≈ Spring @Transactional 边界):提交/回滚收口在这一处。

    两处修正(迁移时的历史坑,留字备忘):
      1) class_ 原来误传 DeclarativeBase(那是建表基类,不是会话类)→ AsyncSession;
      2) 裸 except 吞异常不回抛,会吞出"接口 200 但数据没落库"的诡异 → raise。
    finally 的 session.close() 也由 async with 的 __aexit__ 接管,不用手写。
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
