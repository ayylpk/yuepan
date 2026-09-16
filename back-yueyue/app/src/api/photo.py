"""相册接口层(≈ @Controller /photo):只管收发,规则全在 service。

9/16 补全:初稿只有半行没写完的 page(连 tags 都是从 diary 抄漏的),整层重写。
读公开、写要登录 —— 对齐 project 的写保护口径;
上传走 multipart(浏览器 <input type=file> 原生姿势),不是 JSON base64 那种歪门。

两条签名纪律(都是这仓库付过学费的):
  1. 路由顺序:/page 必须声明在 /{photo_id} 之前,FastAPI 按注册序匹配,
     不然 "page" 会被 int 路径参数吃掉 422(/projects 记过这条);
  2. 参数顺序:Annotated 依赖(Db/LoginUser/ShowPrivate)不带默认值,一律排在
     带默认值的查询参数/File 字段前面(Python 语法 + FastAPI 0.141 双重要求)。
"""
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config.settings import API_PREFIX
from app.common.result.page_result import PageResult
from app.common.schemas.photo.photo_response import PhotoResponse
from app.common.schemas.photo.photo_update import PhotoUpdate
from app.database.engine import get_db
from app.src.service import photo_service
from app.tools.session import LoginUser, ShowPrivate

router = APIRouter(prefix=f"{API_PREFIX}/photo", tags=["photo"])

Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("/page", response_model=PageResult[PhotoResponse])
async def page_photos_api(
    db: Db,
    show_private: ShowPrivate,
    page: int = 1,
    page_size: int = 10,
    role: int = 0,
):
    total, rows = await photo_service.page_photos(db, page, page_size, role, show_private)
    return PageResult[PhotoResponse].success(data=rows, count=total)


@router.post("", response_model=PhotoResponse)
async def create_photo_api(
    login_user: LoginUser,
    db: Db,
    file: UploadFile = File(..., description="图片文件(jpg/png/gif/webp/bmp)"),
    type: str = Form("", max_length=20, description="相册/分类标签"),
    role: int = Form(0, ge=0, le=1, description="0=公开 1=隐私"),
):
    """上传入库:落盘 + 插行两步及补偿顺序都在 photo_service.create_photo 里。"""
    return await photo_service.create_photo(db, file, type, role)


@router.get("/{photo_id}", response_model=PhotoResponse)
async def get_photo_api(photo_id: int, db: Db, show_private: ShowPrivate):
    return await photo_service.get_photo(db, photo_id, show_private)


@router.get("/{photo_id}/file")
async def get_photo_file_api(photo_id: int, db: Db, show_private: ShowPrivate):
    """出图:前端 <img :src="`/api/photo/${id}/file`"> 直接吃,cookie 自动带、闸门自动过。"""
    return await photo_service.get_photo_file(db, photo_id, show_private)


@router.put("/{photo_id}", response_model=PhotoResponse)
async def update_photo_api(
    photo_id: int,
    data: PhotoUpdate,
    login_user: LoginUser,
    db: Db,
    show_private: ShowPrivate,
):
    return await photo_service.update_photo(db, photo_id, data, show_private)


@router.delete("/{photo_id}")
async def delete_photo_api(
    photo_id: int,
    login_user: LoginUser,
    db: Db,
    show_private: ShowPrivate,
):
    """删除:DB 行和 resources/photo/ 下的磁盘文件一起清(先删行后删盘,顺序在 service)。"""
    await photo_service.delete_photo(db, photo_id, show_private)
    return {"message": "删除成功"}
