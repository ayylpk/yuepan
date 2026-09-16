"""日记业务层(≈ @Service):规则都在这 —— repository 只管取数,api 只管收发。

本模板示范的业务:
  1. 可见性:role=1(隐私)对"未解锁"的请求**彻底不存在**(404,而不是 403,
     免得通过状态码差异猜出"这篇是隐私");
  2. 修改:白名单外字段进不了 SQL;role 允许改(0↔1 上锁/摆回公开);
  3. 分页:页码(1 起)→ offset 的换算在业务层,不脏 SQL。
"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas.diary.diary_response import DiaryResponse
from app.common.schemas.diary.diary_update import DiaryUpdate
from app.src.repositories import diary_repository

ROLE_PUBLIC = 0
ROLE_PRIVATE = 1

# 允许被 PUT 修改的字段白名单:不在表里的、不该动的(id/时间戳)都挡在这
UPDATABLE_FIELDS = {"title", "content", "role"}


async def page_diaries(
    db: AsyncSession,                         # ← 接收 db
    page: int = 1,
    page_size: int = 10,
    role: int = 0,
    show_private: bool = False,
):
    # 9/16 补漏:未解锁小屋时 role 强制回公开 —— ?role=1 白嫖隐私列表的路堵死
    # (真源是 session 里的解锁标记,见 api/diary.py 头部注释;photo 同款同治)
    if not show_private:
        role = ROLE_PUBLIC
    return await diary_repository.select_page(db, page, page_size, role)


async def get_diary(
    db: AsyncSession,
    diary_id: int,
    show_private: bool,
) -> DiaryResponse:
    row = await diary_repository.select_by_id(db, diary_id)
    if row is None or (row.role == ROLE_PRIVATE and not show_private):
        raise HTTPException(status_code=404, detail="日记不存在")
    return DiaryResponse.model_validate(row)


async def create_diary(
    db: AsyncSession,
    title: str,
    content: str,
    role: int = 0,
):
    if not title.strip():
        # ValueError 会变成 500;入参问题就该 400 带 detail,前端弹人话
        raise HTTPException(status_code=400, detail="标题不能为空")

    row = await diary_repository.insert(db, title, content, role)
    if row is None:
        raise HTTPException(status_code=404, detail="日记不存在")
    return DiaryResponse.model_validate(row)


async def update_diary(
    db: AsyncSession,
    diary_id: int,
    dto: DiaryUpdate,
    show_private: bool,
) -> DiaryResponse:
    # 1. 校验存在性 + 隐私权限
    row = await diary_repository.select_by_id(db, diary_id)
    if row is None or (row.role == ROLE_PRIVATE and not show_private):
        raise HTTPException(status_code=404, detail="日记不存在")

    # 2. 只取用户传了的、且允许改的字段
    fields = {
        k: v
        for k, v in dto.model_dump(exclude_unset=True).items()
        if k in UPDATABLE_FIELDS
    }
    if not fields:
        raise HTTPException(status_code=400, detail="没收到任何要修改的字段")

    # 3. 调用 repository 更新
    updated = await diary_repository.update(db, diary_id, fields)
    if updated is None:
        raise HTTPException(status_code=404, detail="日记不存在")

    return DiaryResponse.model_validate(updated)


async def delete_diary(
    db: AsyncSession,
    diary_id: int,
    show_private: bool,
) -> None:
    # 1. 校验存在性 + 隐私权限
    row = await diary_repository.select_by_id(db, diary_id)
    if row is None or (row.role == ROLE_PRIVATE and not show_private):
        raise HTTPException(status_code=404, detail="日记不存在")

    # 2. 调用 repository 删除
    success = await diary_repository.delete(db, diary_id)
    if not success:
        raise HTTPException(status_code=404, detail="日记不存在")