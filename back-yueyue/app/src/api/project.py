"""项目接口层(≈ @Controller /projects):只管收发,规则全在 service。

读公开(ProjectsView 直接吃 GET "");写和绑定要登录。
返回不套 Result 信封,和 diary 模板同款(前端 http.ts 原样过)。
注意 /page 声明在 /{project_id} 之前:FastAPI 按注册序匹配,
不然 "page" 会被当成 int 路径参数吃 422。
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config.settings import API_PREFIX
from app.common.result.page_result import PageResult
from app.common.schemas.project.project_create import ProjectCreate
from app.common.schemas.project.project_manage_response import ProjectManageResponse
from app.common.schemas.project.project_response import ProjectResponse
from app.common.schemas.project.project_update import ProjectUpdate
from app.common.schemas.project.tech_bind import TechBind
from app.database.engine import get_db
from app.src.service import project_service
from app.tools.session import LoginUser

router = APIRouter(prefix=f"{API_PREFIX}/projects", tags=["project"])

Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=list[ProjectResponse])
async def list_projects_api(db: Db):
    """前台项目墙数据源(ProjectsView 现成契约,一条不改)。"""
    return await project_service.list_projects(db)


@router.get("/page", response_model=PageResult[ProjectResponse])
async def page_projects_api(
    page: int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """后台管理表格用。"""
    total, rows = await project_service.page_projects(db, page, page_size)
    return PageResult[ProjectResponse].success(data=rows, count=total)


@router.get("/{project_id}/manage", response_model=ProjectManageResponse)
async def get_project_for_manage_api(project_id: int, db: Db, login_user: LoginUser):
    """编辑弹窗回显专用:比公开 VO 多一个 path(要登录)。"""
    return await project_service.get_for_manage(db, project_id)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project_api(project_id: int, db: Db):
    return await project_service.get_project(db, project_id)


@router.post("", response_model=ProjectResponse)
async def create_project_api(dto: ProjectCreate, db: Db, login_user: LoginUser):
    """新项目:tech_names 里没见过的名字自动入库再绑(弹窗匹配语义)。"""
    return await project_service.create_project(db, dto)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project_api(project_id: int, dto: ProjectUpdate, db: Db, login_user: LoginUser):
    return await project_service.update_project(db, project_id, dto)


@router.put("/{project_id}/techs", response_model=ProjectResponse)
async def bind_techs_api(project_id: int, dto: TechBind, db: Db, login_user: LoginUser):
    """弹窗"保存":全量重绑技术栈。"""
    return await project_service.bind_techs(db, project_id, dto)


@router.delete("/{project_id}")
async def delete_project_api(project_id: int, db: Db, login_user: LoginUser):
    await project_service.delete_project(db, project_id)
    return {"message": "删除成功"}
