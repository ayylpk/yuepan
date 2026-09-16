"""日记接口层(≈ @Controller):只管收发,规则全在 service。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.Result.pageResult import PageResult
from app.common.config.config import API_PREFIX
from app.common.schemas.diary.DiaryCreate import DiaryCreate
from app.common.schemas.diary.DiaryResponse import DiaryResponse
from app.common.schemas.diary.DiaryUpdate import DiaryUpdate
from app.database.db import get_db
from app.src.service import diary_service

router = APIRouter(prefix=f"{API_PREFIX}/diary", tags=["diary"])


@router.get("/page", response_model=PageResult[DiaryResponse])
async def page_diaries_api(
    page: int = 1,
    page_size: int = 10,
    role: int = 0,
    db: AsyncSession = Depends(get_db),
):
    total, rows = await diary_service.page_diaries(db, page, page_size, role)
    return PageResult[DiaryResponse].success(data=rows, count=total)


@router.get("/{diary_id}", response_model=DiaryResponse)
async def get_diary_api(
    diary_id: int,
    show_private: bool = False,
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
    show_private: bool = False,
    db: AsyncSession = Depends(get_db),
):
    return await diary_service.update_diary(db, diary_id, data, show_private)


@router.delete("/{diary_id}")
async def delete_diary_api(
    diary_id: int,
    show_private: bool = False,
    db: AsyncSession = Depends(get_db),
):
    await diary_service.delete_diary(db, diary_id, show_private)
    return {"message": "删除成功"}