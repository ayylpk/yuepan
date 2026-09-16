"""技术栈接口层(≈ @Controller /tech):只管收发,规则全在 service。

读公开(list/page —— 弹窗和项目访客都要看),写要登录(增删改)。
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config.config import API_PREFIX
from app.common.Result.pageResult import PageResult
from app.common.schemas.Tech.TechCreate import TechCreate
from app.common.schemas.Tech.TechResponse import TechResponse
from app.common.schemas.Tech.TechUpdate import TechUpdate
from app.database.db import get_db
from app.src.service import tech_service
from app.tools.session import LoginUser

router = APIRouter(prefix=f"{API_PREFIX}/tech", tags=["tech"])

Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("/list", response_model=list[TechResponse])
async def list_techs_api(db: Db):
    """全量字典(含 ref_count),给项目弹窗和前端本地联想用。"""
    return await tech_service.list_all(db)


@router.get("/page", response_model=PageResult[TechResponse])
async def page_techs_api(
    page: int = 1,
    page_size: int = 10,
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """后台表格用:分页 + 关键词(大小写不敏感,service 归一化)。"""
    total, rows = await tech_service.page(db, page, page_size, keyword)
    return PageResult[TechResponse].success(data=rows, count=total)


@router.post("", response_model=TechResponse)
async def create_tech_api(dto: TechCreate, db: Db, login_user: LoginUser):
    """手动新增;任意大小写撞已有记录时幂等返回那条(不报重复)。"""
    return await tech_service.create(db, dto)


@router.put("/{tech_id}", response_model=TechResponse)
async def update_tech_api(tech_id: int, dto: TechUpdate, db: Db, login_user: LoginUser):
    return await tech_service.update(db, tech_id, dto)


@router.delete("/{tech_id}")
async def delete_tech_api(tech_id: int, db: Db, login_user: LoginUser):
    await tech_service.delete(db, tech_id)
    return {"message": "删除成功"}
