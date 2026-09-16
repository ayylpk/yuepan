"""实体层(Java 视角:@Entity 全家)。9/16 从原 database/db.py 拆出。

表结构靠 create_all 长出来,只建不改 —— 开发期改列了直接删对应表重跑
(见 bootstrap.py 顶部的迁移备忘)。
"""
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.engine import Base


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


class CodeFileIndex(Base):
    """代码索引表:一行 = 项目里的一个文件;目录树由 path 列派生,不建目录行。

    9/16 改名:原类 Files / 表 files → CodeFileIndex / code_file_index,
    把 "file" 这个词让给真正的资料上传模块(File 表)—— 此前"Files"一词三义
    (索引表/resources 目录/上传 DTO)正是目录混乱的重灾区。
    索引数据可整项目重建(code_indexer --all),改名迁移 = drop 旧表 + reindex,零损失。

    列口径(初稿保留):
      - project_id 可空:空 = 不属于任何项目的散文件(不进任何树,未来的片段库);
      - path 是相对 project.path 的路径,统一正斜杠("src/api/http.ts"),
        前端 CodeView 的 buildTree() 拿平铺路径拼嵌套树 —— 目录层级是算出来的,不存库;
      - type 小写扩展名,无点不带帽("ts"/"vue"/"py",无扩展名空串);
      - 不建 (project_id, path) 唯一约束:project_id 可空时 SQLite 视 NULL
        互不相等,约束管不住散文件,去重由 indexer 的全删重插策略保证。
    """

    __tablename__ = "code_file_index"

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
    """相册:一行 = resources/photo/ 下的一个磁盘文件。

    path 存**相对 resources/ 的正斜杠路径**("photo/20260916213045_k7fp.jpg"),
    不存绝对路径 —— 换机器/换部署目录只改 settings.RESOURCES_DIR 一处;
    磁盘文件名 = 时间戳+4位随机字符(生成逻辑在 tools/storage.py),
    原始文件名留在 name 列做展示用。
    role 沿用全站可见性口径:0 公开 / 1 隐私(未解锁小屋时按"不存在"处理)。
    """

    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(20), default="")  # 相册/分类标签
    name: Mapped[str] = mapped_column(String(255), default="")  # 原始文件名(展示)
    role: Mapped[int] = mapped_column(Integer, default=0)
    path: Mapped[str] = mapped_column(String(200))
    size: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class File(Base):
    """资料库(小站主业:放各种资料/文件):一行 = resources/file/ 下一个磁盘文件。

    存储口径和 Photo 完全一致(相对 resources/ 路径、时间戳+4随机命名、
    role 可见性),差别只在收的文件类型(见 storage.py 的白/黑名单)。
    """

    __tablename__ = "file"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), default="")  # 原始文件名(展示+下载名)
    type: Mapped[str] = mapped_column(String(20), default="")  # 小写扩展名,不带点
    role: Mapped[int] = mapped_column(Integer, default=0)
    path: Mapped[str] = mapped_column(String(200))
    size: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
