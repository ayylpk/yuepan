"""相册业务层(≈ @Service):规则都在这 —— repository 只管取数,api 只管收发。

9/16 补全时的两块新业务(需求正身:insert/delete 必须联动磁盘):
  1. 上传落盘:调 tools/storage.save(命名/白名单/魔数/上限全在那),
     **先落盘再插行**,插行炸了补偿删盘 —— 不留"盘上有、库里无"的孤儿文件;
  2. 删除销户:**先删行成功再删盘** —— 指针永远比文件活得久,
     反序会留下"库里查不到、盘上见不得人"的文件,那才是真丢了(删不掉也没人知道它存在)。

可见性照抄 diary:role=1 未解锁 = 404(防状态码探测);初稿 service 把 role
参数直接吞了(调 repo 不传),这次也一并接上。
"""
import mimetypes

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas.photo.photo_response import PhotoResponse
from app.common.schemas.photo.photo_update import PhotoUpdate
from app.database.models import Photo
from app.src.repositories import photo_repository
from app.tools import storage
from app.tools.storage import IMAGE_EXTS

ROLE_PUBLIC = 0
ROLE_PRIVATE = 1

# PUT 可改字段白名单(name/size/path 绑磁盘,不开放 —— 见 PhotoUpdate docstring)
UPDATABLE_FIELDS = {"type", "role"}


async def _require_visible(db: AsyncSession, photo_id: int, show_private: bool) -> Photo:
    """存在性 + 隐私闸门:隐私图对未解锁请求"彻底不存在"(404,不是 403)。"""
    row = await photo_repository.select_by_id(db, photo_id)
    if row is None or (row.role == ROLE_PRIVATE and not show_private):
        raise HTTPException(status_code=404, detail="照片不存在")
    return row


async def page_photos(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    role: int = ROLE_PUBLIC,
    show_private: bool = False,
):
    # 未解锁小屋时 role 强制回公开 —— 堵死 ?role=1 白嫖隐私列表的路
    # (diary page 同款洞,这次一起补)
    if not show_private:
        role = ROLE_PUBLIC
    return await photo_repository.select_page(db, page, page_size, role)


async def get_photo(db: AsyncSession, photo_id: int, show_private: bool) -> PhotoResponse:
    row = await _require_visible(db, photo_id, show_private)
    return PhotoResponse.model_validate(row)


async def get_photo_file(
    db: AsyncSession, photo_id: int, show_private: bool
) -> FileResponse:
    """出图:闸门过了才碰磁盘。media_type 按扩展名猜,猜不动一律 octet-stream。"""
    row = await _require_visible(db, photo_id, show_private)
    target = storage.resolve_saved(row.path)
    if not target.is_file():
        # 库里有行、盘上没文件 = 有人手工删了文件没走 DELETE 接口,如实报
        raise HTTPException(status_code=404, detail="磁盘文件不存在,可能已被手动清理")
    media_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
    return FileResponse(target, media_type=media_type)


async def create_photo(
    db: AsyncSession,
    upload: UploadFile,
    type: str = "",
    role: int = ROLE_PUBLIC,
) -> PhotoResponse:
    if len(type) > 20:
        raise HTTPException(status_code=400, detail="分类标签最长 20 字")
    if role not in (ROLE_PUBLIC, ROLE_PRIVATE):
        raise HTTPException(status_code=400, detail="role 只能是 0(公开)或 1(隐私)")

    # 1) 落盘(storage 里过类型/大小/魔数三关,炸了它自己收尾,不脏目录)
    rel_path, size = await storage.save(
        "photo", upload, allowed_exts=IMAGE_EXTS, magic_check=True
    )

    # 2) 插行;失败补偿删盘,两界不长期欠账
    try:
        row = await photo_repository.insert(
            db,
            {
                "type": type,
                "name": storage.original_name(upload.filename or ""),
                "role": role,
                "path": rel_path,
                "size": size,
            },
        )
    except Exception:
        storage.delete(rel_path)
        raise
    return PhotoResponse.model_validate(row)


async def update_photo(
    db: AsyncSession, photo_id: int, dto: PhotoUpdate, show_private: bool
) -> PhotoResponse:
    await _require_visible(db, photo_id, show_private)  # 1) 存在 + 隐私

    fields = {
        k: v
        for k, v in dto.model_dump(exclude_unset=True).items()
        if k in UPDATABLE_FIELDS and v is not None
    }
    if not fields:
        raise HTTPException(status_code=400, detail="没收到任何要修改的字段")

    updated = await photo_repository.update(db, photo_id, fields)  # 2) 改
    if updated is None:
        raise HTTPException(status_code=404, detail="照片不存在")
    return PhotoResponse.model_validate(updated)


async def delete_photo(db: AsyncSession, photo_id: int, show_private: bool) -> None:
    row = await _require_visible(db, photo_id, show_private)

    # 先删行(库里销户),成功后再删盘(磁盘销尸)—— 顺序不许反,见文件头
    success = await photo_repository.delete(db, photo_id)
    if not success:
        raise HTTPException(status_code=404, detail="照片不存在")
    storage.delete(row.path)
