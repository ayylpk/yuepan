"""日记接口层(≈ @Controller):只管收发,规则全在 service。

9/16 补漏:show_private 原来是**查询参数** —— 谁都能 ?show_private=true
一键绕过小屋(README TODO 2 和 PrivateView 注释都认定"可见性真源在服务端
session",这条旁路违背的正是自家口径)。整层换成 session.ShowPrivate 依赖:
解锁态只认 /api/auth/private/unlock 写进 session 的标记,参数消失;
前端从没传过这个参数,换完无感。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config.settings import API_PREFIX
from app.common.result.page_result import PageResult
from app.common.schemas.diary.diary_create import DiaryCreate
from app.common.schemas.diary.diary_response import DiaryResponse
from app.common.schemas.diary.diary_update import DiaryUpdate
from app.database.engine import get_db
from app.src.service import diary_service
from app.tools.session import ShowPrivate

router = APIRouter(prefix=f"{API_PREFIX}/diary", tags=["diary"])


@router.get("/page", response_model=PageResult[DiaryResponse])
async def page_diaries_api(
    show_private: ShowPrivate,
    page: int = 1,
    page_size: int = 10,
    role: int = 0,
    db: AsyncSession = Depends(get_db),
):
    total, rows = await diary_service.page_diaries(db, page, page_size, role, show_private)
    return PageResult[DiaryResponse].success(data=rows, count=total)


@router.get("/{diary_id}", response_model=DiaryResponse)
async def get_diary_api(
    diary_id: int,
    show_private: ShowPrivate,
    db: AsyncSession = Depends(get_db),
):
    return await diary_service.get_diary(db, diary_id, show_private)


@router.post("", response_model=DiaryResponse)
async def create_diary_api(
    data: DiaryCreate,
    db: AsyncSession = Depends(get_db),
):
    return await diary_service.create_diary(db, data.title, data.content, data.role)


@router.put("/{diary_id}", response_model=DiaryResponse)
async def update_diary_api(
    diary_id: int,
    data: DiaryUpdate,
    show_private: ShowPrivate,
    db: AsyncSession = Depends(get_db),
):
    return await diary_service.update_diary(db, diary_id, data, show_private)


@router.delete("/{diary_id}")
async def delete_diary_api(
    diary_id: int,
    show_private: ShowPrivate,
    db: AsyncSession = Depends(get_db),
):
    await diary_service.delete_diary(db, diary_id, show_private)
    return {"message": "删除成功"}
