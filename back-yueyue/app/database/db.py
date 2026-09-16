"""SQLAlchemy 模型层(Java 视角:entity + DataSource 配置)。

9/16 从 sqlite3 裸连接迁到 SQLAlchemy 2.0 async:
  - 一个库文件 yueyue.db(User/Diary/Project/TechStack/ProjectTech/Files 全在这);
  - engine 用 create_async_engine,2.0 对 sqlite:// URL 自动走 aiosqlite 驱动(已补依赖);
  - 表结构靠 create_all 长出来,只建不改 —— 开发期改列了直接删 .db 文件重跑。

库文件落 app/database/resources/database/,engine 建之前先 mkdir 父目录,
SQLite 不会替你建目录,首连就是 "unable to open database file"。
"""
from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    func,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "resources" / "database" / "yueyue.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# 注意:URL 必须显式写 +aiosqlite 驱动,create_async_engine 不会替你从 sqlite:// 自动换
# (9/16 实测:自动换驱动的说法是错的,pysqlite 直接报 "requires an async driver")
engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}")


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(100))
    private_password: Mapped[str] = mapped_column(String(100))
    # 资料三件套给默认值:种子账号只带用户名密码,不传也插得进去
    qq: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(100), unique=True, default="")
    phone: Mapped[str] = mapped_column(String(20), default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Diary(Base):
    __tablename__ = "diary"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(120))
    content: Mapped[str] = mapped_column(Text, default="")
    role: Mapped[int] = mapped_column(default=0)

    # 日期字段
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Project(Base):
    """项目表:代码模块的锚点。

    path 是本机目录的绝对路径,只留在后端 —— 前端 VO 不回传它(公网站点泄露目录结构),
    读文件时后端内部拿 path 拼相对路径(见 code_service 的 jail)。
    repo 是挂到"在线看代码"白名单用的仓库名,空则按 name 匹配。
    """

    __tablename__ = "project"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    code: Mapped[str] = mapped_column(String(8), default="📦")  # emoji 占位图标
    period: Mapped[str] = mapped_column(String(40), default="")  # 时间段,手填任意口径
    path: Mapped[str] = mapped_column(String(260), default="")  # 本地目录;非空才进代码白名单
    repo: Mapped[str] = mapped_column(String(100), default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )


class TechStack(Base):
    """技术栈字典表(用户手动填写,支持 CRUD)。

    大小写不敏感的落地:name 存原样("Vue"),name_key 存 name.strip().lower()
    并加唯一索引 —— 去重和弹窗匹配全按 name_key 走。SQLite 默认 BINARY 排序
    不分大小写这事它不管,归一化放写入侧最稳(Java 类比:入库前自己 normalize)。
    """

    __tablename__ = "tech_stack"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))
    name_key: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ProjectTech(Base):
    """项目 ↔ 技术栈 多对多中间表(≈ MyBatis 的 m2m relation 表)。"""

    __tablename__ = "project_tech"

    project_id: Mapped[int] = mapped_column(ForeignKey("project.id"))
    tech_id: Mapped[int] = mapped_column(ForeignKey("tech_stack.id"))

    __table_args__ = (PrimaryKeyConstraint("project_id", "tech_id"),)


class Files(Base):
    """代码索引表:一行 = 项目里的一个文件;目录树由 path 列派生,不建目录行。

    你的初稿(id/path/type/created_at)保留表名和列名,补了归属和大小:
      - project_id 可空:空 = 不属于任何项目的散文件(不进任何树,未来的片段库);
      - path 是相对 project.path 的路径,统一正斜杠("src/api/http.ts"),
        前端 CodeView 的 buildTree() 拿平铺路径拼嵌套树 —— 目录层级是算出来的,
        不存库;站外移动/删除文件时索引必然滞后,所以 reindex 是"整项目重建",
        没有双写漂移问题;
      - type 就是你那列:小写扩展名,无点不带帽("ts"/"vue"/"py",无扩展名空串);
      - 不建 (project_id, path) 唯一约束:project_id 可空时 SQLite 视 NULL
        互不相等,约束管不住散文件,去重由 indexer 的全删重插策略保证。
    """

    __tablename__ = "files"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("project.id"), index=True, nullable=True
    )
    path: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(20), default="")
    size: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

class Photo(Base):
    __tablename__ = "photos"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(20), default="")
    role: Mapped[str] = mapped_column(String(20), default="")
    path: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())



async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# 原稿这里还有个自带的 lifespan,和 main.py 那个是重复的真相源,删了;
# 启动钩子统一走 main.py lifespan → app/tools/db.py 的 init_db()。

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """请求级 session(≈ Spring @Transactional 边界):提交/回滚收口在这一处。

    两处修正:
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
