"""启动初始化钩子(≈ Spring 的 ApplicationRunner)。

9/16 从 tools/db.py 搬进来:和 engine/models 同一个包,tools/ 里不再留 "db"
撞名文件。main.py 的 lifespan 调 init_db():建表(幂等)+ 空 user 表塞种子账号。

迁移备忘(9/16 一次性,已执行):photos(空表)和 files(索引表,已改名
code_file_index)两张旧表直接 DROP 后由 create_all 长新结构,索引数据用
`uv run python -m app.tools.code_indexer --all` 重建;有数据的表零接触。
"""
from sqlalchemy import select

# 建表前必须让所有实体挂上 Base.metadata(import models 这个动作本身即注册)
from app.database import models  # noqa: F401
from app.database.engine import AsyncSessionLocal, Base, engine
from app.tools.security import hash_password

# 种子账号(本地开发用;上线前记得进设置页改掉)
SEED_USERNAME = "admin"
SEED_PASSWORD = "123456"
SEED_PRIVATE_PASSWORD = "123456"


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def init_db() -> None:
    await create_tables()
    await seed_admin()


async def seed_admin() -> None:
    """空表才种:入库前哈希(库里永远不写明文),重启不重复插。"""
    async with AsyncSessionLocal() as session:
        has_user = await session.scalar(select(models.User.id).limit(1))
        if has_user is not None:
            return
        session.add(
            models.User(
                username=SEED_USERNAME,
                password=hash_password(SEED_PASSWORD),
                private_password=hash_password(SEED_PRIVATE_PASSWORD),
            )
        )
        await session.commit()
