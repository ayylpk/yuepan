"""代码索引数据访问层(≈ CodeMapper):code_file_index 表(代码索引)的读写都在这。

索引策略是"整项目重建"(reindex 全删重插),所以这里没有单行 upsert ——
目录树由 path 列派生,不存目录行(见 models.py CodeFileIndex 的注释)。
"""
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CodeFileIndex


async def select_paths(db: AsyncSession, project_id: int) -> list[CodeFileIndex]:
    stmt = (
        select(CodeFileIndex)
        .where(CodeFileIndex.project_id == project_id)
        .order_by(CodeFileIndex.path)
    )
    return list((await db.execute(stmt)).scalars().all())


async def rebuild_index(db: AsyncSession, project_id: int, rows: list[dict[str, Any]]) -> int:
    """整项目重建:删该项目的旧索引行,批量插新行,一次 commit。

    rows = [{path, type, size}, ...](indexer 扫盘产出的干净数据,这里不再判)。
    返回写入条数。
    """
    await db.execute(delete(CodeFileIndex).where(CodeFileIndex.project_id == project_id))
    for row in rows:
        db.add(CodeFileIndex(project_id=project_id, **row))
    await db.commit()
    return len(rows)


async def detach_project_files(db: AsyncSession, project_id: int) -> int:
    """项目删除时调用:索引行不删,project_id 置空 —— 口径是"空=不属于项目",
    散文件留给未来的片段功能,而不是跟着项目陪葬。返回置空条数。
    """
    result = await db.execute(
        update(CodeFileIndex).where(CodeFileIndex.project_id == project_id).values(project_id=None)
    )
    await db.commit()
    return result.rowcount or 0


async def select_one(db: AsyncSession, project_id: int, path: str) -> CodeFileIndex | None:
    stmt = select(CodeFileIndex).where(
        CodeFileIndex.project_id == project_id, CodeFileIndex.path == path
    )
    return (await db.execute(stmt)).scalars().first()
