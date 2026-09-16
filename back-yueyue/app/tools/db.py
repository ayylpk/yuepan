"""启动初始化钩子(≈ Spring 的 ApplicationRunner)。

main.py 的 lifespan 调 init_db():建表(幂等)+ 空 user 表塞种子账号。
9/16 备忘:这文件原来是无 SQLAlchemy 时代的 sqlite3 连接层(get_user_db 等),
迁 async 后连接职责搬去 app/database/db.py,这里重建为"只管启动动作"。
"""
from sqlalchemy import select

from app.database.db import AsyncSessionLocal, User, create_tables
from app.tools.security import hash_password

# 种子账号(本地开发用;上线前记得进设置页改掉)
SEED_USERNAME = "admin"
SEED_PASSWORD = "123456"
SEED_PRIVATE_PASSWORD = "123456"


async def init_db() -> None:
    await create_tables()
    await seed_admin()


async def seed_admin() -> None:
    """空表才种:入库前哈希(库里永远不写明文),重启不重复插。"""
    async with AsyncSessionLocal() as session:
        has_user = await session.scalar(select(User.id).limit(1))
        if has_user is not None:
            return
        session.add(
            User(
                username=SEED_USERNAME,
                password=hash_password(SEED_PASSWORD),
                private_password=hash_password(SEED_PRIVATE_PASSWORD),
            )
        )
        await session.commit()
