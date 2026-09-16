"""资料库接口层(≈ @Controller /file):photo 的同构镜像,签名纪律同款。

路由前缀单数 /api/file,和 /api/diary /api/photo /api/user 一个口径
(/api/projects 是历史遗留,新模块不再扩大例外)。
"""
from typing import Annotated

from fastapi import APIRouter, Depends, File as FormFile, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config.settings import API_PREFIX
from app.common.result.page_result import PageResult
from app.common.schemas.file.file_info_response import FileInfoResponse
from app.common.schemas.file.file_update import FileUpdate
from app.database.engine import get_db
from app.src.service import file_service
from app.tools.session import LoginUser, ShowPrivate

router = APIRouter(prefix=f"{API_PREFIX}/file", tags=["file"])

Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("/page", response_model=PageResult[FileInfoResponse])
async def page_files_api(
    db: Db,
    show_private: ShowPrivate,
    page: int = 1,
    page_size: int = 10,
    role: int = 0,
):
    total, rows = await file_service.page_files(db, page, page_size, role, show_private)
    return PageResult[FileInfoResponse].success(data=rows, count=total)


@router.post("", response_model=FileInfoResponse)
async def create_file_api(
    login_user: LoginUser,
    db: Db,
    file: UploadFile = FormFile(..., description="资料文件(pdf/zip/图片…可执行除外)"),
    role: int = Form(0, ge=0, le=1, description="0=公开 1=隐私"),
):
    """上传资料:落盘 resources/file/ + 插行,展示名取原始文件名(规则在 service)。"""
    return await file_service.create_file(db, file, role)


@router.get("/{file_id}", response_model=FileInfoResponse)
async def get_file_api(file_id: int, db: Db, show_private: ShowPrivate):
    return await file_service.get_file(db, file_id, show_private)


@router.get("/{file_id}/download")
async def download_file_api(file_id: int, db: Db, show_private: ShowPrivate):
    """下载:attachment + 原始文件名(a 标签 href 直接吃,cookie 自动带)。"""
    return await file_service.download_file(db, file_id, show_private)


@router.put("/{file_id}", response_model=FileInfoResponse)
async def update_file_api(
    file_id: int,
    data: FileUpdate,
    login_user: LoginUser,
    db: Db,
    show_private: ShowPrivate,
):
    return await file_service.update_file(db, file_id, data, show_private)


@router.delete("/{file_id}")
async def delete_file_api(
    file_id: int,
    login_user: LoginUser,
    db: Db,
    show_private: ShowPrivate,
):
    """删除:DB 行和 resources/file/ 下的磁盘文件一起清(先删行后删盘)。"""
    await file_service.delete_file(db, file_id, show_private)
    return {"message": "删除成功"}
