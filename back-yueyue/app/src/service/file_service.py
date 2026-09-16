"""资料库业务层(≈ @Service):photo_service 的镜像,规则一字不差同一家。

需求 3"其它文件的存储是同样的道理"的落点:
  - 同样走 tools/storage.save/delete(命名、大小上限、越狱检查全共用一份实现);
  - 差别只有两处 —— 收的类型(file 用可执行黑名单而非图片白名单)、
    出图变下载(Content-Disposition: attachment + 原始文件名)。
"""
import mimetypes

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas.file.file_info_response import FileInfoResponse
from app.common.schemas.file.file_update import FileUpdate
from app.database.models import File
from app.src.repositories import file_repository
from app.tools import storage
from app.tools.storage import FILE_EXT_BLACKLIST

ROLE_PUBLIC = 0
ROLE_PRIVATE = 1

# type 不开放(和磁盘文件的扩展名绑死),能改的只有展示名和可见性
UPDATABLE_FIELDS = {"name", "role"}


async def _require_visible(db: AsyncSession, file_id: int, show_private: bool) -> File:
    """存在性 + 隐私闸门:隐私资料对未解锁请求"彻底不存在"(404,不是 403)。"""
    row = await file_repository.select_by_id(db, file_id)
    if row is None or (row.role == ROLE_PRIVATE and not show_private):
        raise HTTPException(status_code=404, detail="文件不存在")
    return row


async def page_files(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    role: int = ROLE_PUBLIC,
    show_private: bool = False,
):
    if not show_private:
        role = ROLE_PUBLIC  # 未解锁时 role=1 查询按"没有这种东西"处理
    return await file_repository.select_page(db, page, page_size, role)


async def get_file(db: AsyncSession, file_id: int, show_private: bool) -> FileInfoResponse:
    row = await _require_visible(db, file_id, show_private)
    return FileInfoResponse.model_validate(row)


async def download_file(
    db: AsyncSession, file_id: int, show_private: bool
) -> FileResponse:
    """下载:attachment 让浏览器存盘而不是就地打开,xss 类文件也少一层侥幸。"""
    row = await _require_visible(db, file_id, show_private)
    target = storage.resolve_saved(row.path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="磁盘文件不存在,可能已被手动清理")
    media_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
    return FileResponse(target, media_type=media_type, filename=row.name or target.name)


async def create_file(
    db: AsyncSession,
    upload: UploadFile,
    role: int = ROLE_PUBLIC,
) -> FileInfoResponse:
    if role not in (ROLE_PUBLIC, ROLE_PRIVATE):
        raise HTTPException(status_code=400, detail="role 只能是 0(公开)或 1(隐私)")

    # 1) 落盘:黑名单挡可执行,50MB 上限(storage 里 MAX_BYTES["file"])
    rel_path, size = await storage.save(
        "file", upload, blacklisted_exts=FILE_EXT_BLACKLIST
    )

    # 2) 插行;失败补偿删盘 —— 顺序纪律同 photo_service,文件头两行就是
    try:
        row = await file_repository.insert(
            db,
            {
                "name": storage.original_name(upload.filename or ""),
                "type": rel_path.rsplit(".", 1)[-1] if "." in rel_path else "",
                "role": role,
                "path": rel_path,
                "size": size,
            },
        )
    except Exception:
        storage.delete(rel_path)
        raise
    return FileInfoResponse.model_validate(row)


async def update_file(
    db: AsyncSession, file_id: int, dto: FileUpdate, show_private: bool
) -> FileInfoResponse:
    await _require_visible(db, file_id, show_private)

    fields = {
        k: v
        for k, v in dto.model_dump(exclude_unset=True).items()
        if k in UPDATABLE_FIELDS and v is not None
    }
    if not fields:
        raise HTTPException(status_code=400, detail="没收到任何要修改的字段")

    updated = await file_repository.update(db, file_id, fields)
    if updated is None:
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileInfoResponse.model_validate(updated)


async def delete_file(db: AsyncSession, file_id: int, show_private: bool) -> None:
    row = await _require_visible(db, file_id, show_private)

    # 先删行(库里销户),成功后再删盘(磁盘销尸)—— 顺序不许反
    success = await file_repository.delete(db, file_id)
    if not success:
        raise HTTPException(status_code=404, detail="文件不存在")
    storage.delete(row.path)
