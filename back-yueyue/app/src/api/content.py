"""人物志与动漫展示 API。图片复用 resources/photo 存储，权限继承父条目。"""
import mimetypes
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config.settings import API_PREFIX
from app.database import models
from app.database.engine import get_db
from app.tools import storage
from app.tools.session import LoginUser, ShowPrivate

router = APIRouter(prefix=API_PREFIX, tags=["content"])
Db = Annotated[AsyncSession, Depends(get_db)]


class CharacterPayload(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    subtitle: str = ""
    bio: str = ""
    visibility: str = "public"
    fields: list[dict[str, str]] = Field(default_factory=list)


class AnimePayload(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    subtitle: str = ""
    description: str = ""
    visibility: str = "public"


class SeasonPayload(BaseModel):
    season_number: int = Field(default=1, ge=1)
    title: str = ""


class EpisodePayload(BaseModel):
    episode_number: int = Field(default=1, ge=1)
    title: str = ""
    feeling: str = ""


def _role(visibility: str) -> int:
    if visibility not in ("public", "private"):
        raise HTTPException(400, "visibility 只能是 public 或 private")
    return 1 if visibility == "private" else 0


def _visible(row, show_private: bool):
    if row is None or (row.role == 1 and not show_private):
        raise HTTPException(404, "内容不存在")
    return row


def _fmt_time(value):
    """时间统一成和 diary/file/photo 一样的 "YYYY-MM-DD HH:MM:SS"。

    原来直接把 datetime 交给 FastAPI,序列化成 ISO("2026-10-19T02:55:46"),
    前端 slice(0,16) 会在界面上留下一个 T("2026-10-19T02:55")。
    """
    return value.strftime("%Y-%m-%d %H:%M:%S") if hasattr(value, "strftime") else value


def _base(row):
    return {
        "id": row.id,
        "visibility": "private" if row.role else "public",
        "created_at": _fmt_time(row.created_at),
        "updated_at": _fmt_time(getattr(row, "updated_at", row.created_at)),
    }


async def _character_data(row, db):
    data = _base(row) | {"name": row.name, "subtitle": row.subtitle, "bio": row.bio, "cover_image_id": row.cover_image_id}
    fields = (await db.scalars(select(models.CharacterField).where(models.CharacterField.character_id == row.id).order_by(models.CharacterField.sort_order, models.CharacterField.id))).all()
    images = (await db.scalars(select(models.CharacterImage).where(models.CharacterImage.character_id == row.id).order_by(models.CharacterImage.sort_order, models.CharacterImage.id))).all()
    data["fields"] = [{"id": f.id, "label": f.label, "value": f.value} for f in fields]
    data["images"] = [{"id": i.id, "name": i.name, "url": f"/api/content/images/character/{i.id}"} for i in images]
    return data


async def _anime_data(row, db):
    data = _base(row) | {"title": row.title, "subtitle": row.subtitle, "description": row.description, "cover_image_id": row.cover_image_id}
    seasons = (await db.scalars(select(models.AnimeSeason).where(models.AnimeSeason.work_id == row.id).order_by(models.AnimeSeason.sort_order, models.AnimeSeason.season_number))).all()
    images = (await db.scalars(select(models.AnimeImage).where(models.AnimeImage.work_id == row.id).order_by(models.AnimeImage.sort_order, models.AnimeImage.id))).all()
    out = []
    for s in seasons:
        eps = (await db.scalars(select(models.AnimeEpisode).where(models.AnimeEpisode.season_id == s.id).order_by(models.AnimeEpisode.sort_order, models.AnimeEpisode.episode_number))).all()
        out.append({"id": s.id, "season_number": s.season_number, "title": s.title, "episodes": [{"id": e.id, "episode_number": e.episode_number, "title": e.title, "feeling": e.feeling} for e in eps]})
    data["seasons"] = out
    data["images"] = [{"id": i.id, "name": i.name, "episode_id": i.episode_id, "url": f"/api/content/images/anime/{i.id}"} for i in images]
    return data


@router.get("/characters")
async def list_characters(db: Db, show_private: ShowPrivate):
    """列表只回摘要(10/19):只带封面那一张,不再把每个人的全部图片塞进响应。

    列表页实际只需要 名字/副标题/简介 + 封面 + 图集数量;
    原来的做法对每个人调 _character_data,把 images 整个数组都发下去。
    → 现在返回 CharacterSummary:{..., cover: {id,name,url}|null, image_count}
      完整图集走 GET /api/characters/{id}。
    封面与计数都是"一次 in_ 查询",不是每人查一次。
    注意 image_count 是**图集张数(不含肖像)** —— 和详情页「批量图片 N」的口径一致。
    """
    rows = (await db.scalars(select(models.CharacterProfile).order_by(models.CharacterProfile.updated_at.desc()))).all()
    visible = [r for r in rows if r.role == 0 or show_private]
    if not visible:
        return []
    ids = [r.id for r in visible]
    counts = dict((await db.execute(
        select(models.CharacterImage.character_id, func.count())
        .where(models.CharacterImage.character_id.in_(ids))
        .group_by(models.CharacterImage.character_id)
    )).all())
    cover_ids = [r.cover_image_id for r in visible if r.cover_image_id]
    covers = {}
    if cover_ids:
        for img in (await db.scalars(select(models.CharacterImage).where(models.CharacterImage.id.in_(cover_ids)))).all():
            covers[img.id] = {"id": img.id, "name": img.name, "url": f"/api/content/images/character/{img.id}"}
    return [
        _base(r) | {
            "name": r.name,
            "subtitle": r.subtitle,
            "bio": r.bio,
            "cover_image_id": r.cover_image_id,
            "cover": covers.get(r.cover_image_id) if r.cover_image_id else None,
            # 肖像也算在 character_image 里,这里减掉它,口径与详情页「批量图片 N」一致
            "image_count": max(0, counts.get(r.id, 0) - (1 if r.cover_image_id in covers else 0)),
        }
        for r in visible
    ]


@router.post("/characters")
async def create_character(payload: CharacterPayload, login: LoginUser, db: Db):
    row = models.CharacterProfile(name=payload.name.strip(), subtitle=payload.subtitle, bio=payload.bio, role=_role(payload.visibility))
    db.add(row); await db.flush()
    for idx, item in enumerate(payload.fields):
        label, value = str(item.get("label", "")).strip(), str(item.get("value", ""))
        if label: db.add(models.CharacterField(character_id=row.id, label=label, value=value, sort_order=idx))
    await db.commit(); await db.refresh(row)
    return await _character_data(row, db)


@router.get("/characters/{character_id}")
async def get_character(character_id: int, db: Db, show_private: ShowPrivate):
    return await _character_data(_visible(await db.get(models.CharacterProfile, character_id), show_private), db)


@router.put("/characters/{character_id}")
async def update_character(character_id: int, payload: CharacterPayload, login: LoginUser, db: Db, show_private: ShowPrivate):
    row = _visible(await db.get(models.CharacterProfile, character_id), show_private)
    row.name, row.subtitle, row.bio, row.role = payload.name.strip(), payload.subtitle, payload.bio, _role(payload.visibility)
    await db.execute(delete(models.CharacterField).where(models.CharacterField.character_id == row.id))
    for idx, item in enumerate(payload.fields):
        label = str(item.get("label", "")).strip()
        if label: db.add(models.CharacterField(character_id=row.id, label=label, value=str(item.get("value", "")), sort_order=idx))
    await db.commit(); return await _character_data(row, db)


@router.post("/characters/{character_id}/images")
async def upload_character_image(character_id: int, login: LoginUser, db: Db, file: UploadFile = File(...)):
    row = await db.get(models.CharacterProfile, character_id)
    if not row: raise HTTPException(404, "人物不存在")
    path, size = await storage.save("photo", file, allowed_exts=storage.IMAGE_EXTS, magic_check=True)
    image = models.CharacterImage(character_id=character_id, path=path, name=storage.original_name(file.filename or ""), size=size)
    db.add(image); await db.commit(); await db.refresh(image)
    return {"id": image.id, "name": image.name, "url": f"/api/content/images/character/{image.id}"}


@router.post("/characters/{character_id}/portrait")
async def upload_character_portrait(character_id: int, login: LoginUser, db: Db, file: UploadFile = File(...)):
    """独立肖像位(简历照片那张):上传后直接置为 cover_image_id。

    与批量图集共用 character_image 表,但语义是"封面"——前端把它从图集里过滤掉单独渲染。
    重新上传只是换一个 cover 指向,旧图仍留在图集里(不主动删用户文件)。
    """
    row = await db.get(models.CharacterProfile, character_id)
    if not row: raise HTTPException(404, "人物不存在")
    path, size = await storage.save("photo", file, allowed_exts=storage.IMAGE_EXTS, magic_check=True)
    image = models.CharacterImage(
        character_id=character_id, path=path,
        name=storage.original_name(file.filename or ""), size=size, sort_order=-1,
    )
    db.add(image); await db.flush()
    row.cover_image_id = image.id
    await db.commit(); await db.refresh(row)
    return await _character_data(row, db)


@router.delete("/characters/{character_id}")
async def delete_character(character_id: int, login: LoginUser, db: Db, show_private: ShowPrivate):
    row = _visible(await db.get(models.CharacterProfile, character_id), show_private)
    imgs = (await db.scalars(select(models.CharacterImage).where(models.CharacterImage.character_id == row.id))).all()
    await db.execute(delete(models.CharacterField).where(models.CharacterField.character_id == row.id))
    await db.execute(delete(models.CharacterImage).where(models.CharacterImage.character_id == row.id))
    await db.delete(row); await db.commit()
    for image in imgs: storage.delete(image.path)
    return {"message": "删除成功"}


@router.get("/anime")
async def list_anime(db: Db, show_private: ShowPrivate):
    """列表只回摘要(10/19):不再把所有作品的季/集/图全塞进响应。

    之前每部作品都带完整 seasons(内含 episodes)+ images,26 张图的作品一次就上百行;
    列表页其实只需要 标题/副标题/简介 + 三个计数。
    → 现在返回 AnimeSummary:{..., image_count, season_count, episode_count},
    详细内容走 GET /api/anime/{work_id}。
    三个计数用三条 group by 一次算完(不是每部作品查三次,N+1 也一并消掉)。
    """
    rows = (await db.scalars(select(models.AnimeWork).order_by(models.AnimeWork.updated_at.desc()))).all()
    visible = [r for r in rows if r.role == 0 or show_private]
    if not visible:
        return []
    ids = [r.id for r in visible]
    image_counts = dict((await db.execute(
        select(models.AnimeImage.work_id, func.count())
        .where(models.AnimeImage.work_id.in_(ids))
        .group_by(models.AnimeImage.work_id)
    )).all())
    season_counts = dict((await db.execute(
        select(models.AnimeSeason.work_id, func.count())
        .where(models.AnimeSeason.work_id.in_(ids))
        .group_by(models.AnimeSeason.work_id)
    )).all())
    episode_counts = dict((await db.execute(
        select(models.AnimeSeason.work_id, func.count(models.AnimeEpisode.id))
        .join(models.AnimeEpisode, models.AnimeEpisode.season_id == models.AnimeSeason.id)
        .where(models.AnimeSeason.work_id.in_(ids))
        .group_by(models.AnimeSeason.work_id)
    )).all())
    return [
        _base(r) | {
            "title": r.title,
            "subtitle": r.subtitle,
            "description": r.description,
            "cover_image_id": r.cover_image_id,
            "image_count": image_counts.get(r.id, 0),
            "season_count": season_counts.get(r.id, 0),
            "episode_count": episode_counts.get(r.id, 0),
        }
        for r in visible
    ]


@router.post("/anime")
async def create_anime(payload: AnimePayload, login: LoginUser, db: Db):
    row = models.AnimeWork(title=payload.title.strip(), subtitle=payload.subtitle, description=payload.description, role=_role(payload.visibility))
    db.add(row); await db.commit(); await db.refresh(row); return await _anime_data(row, db)


@router.get("/anime/{work_id}")
async def get_anime(work_id: int, db: Db, show_private: ShowPrivate):
    return await _anime_data(_visible(await db.get(models.AnimeWork, work_id), show_private), db)


@router.put("/anime/{work_id}")
async def update_anime(work_id: int, payload: AnimePayload, login: LoginUser, db: Db, show_private: ShowPrivate):
    row = _visible(await db.get(models.AnimeWork, work_id), show_private)
    row.title, row.subtitle, row.description, row.role = payload.title.strip(), payload.subtitle, payload.description, _role(payload.visibility)
    await db.commit(); return await _anime_data(row, db)


@router.post("/anime/{work_id}/seasons")
async def create_season(work_id: int, payload: SeasonPayload, login: LoginUser, db: Db):
    if not await db.get(models.AnimeWork, work_id): raise HTTPException(404, "作品不存在")
    row = models.AnimeSeason(work_id=work_id, season_number=payload.season_number, title=payload.title)
    db.add(row); await db.commit(); await db.refresh(row); return {"id": row.id, "season_number": row.season_number, "title": row.title, "episodes": []}


@router.post("/anime/seasons/{season_id}/episodes")
async def create_episode(season_id: int, payload: EpisodePayload, login: LoginUser, db: Db):
    if not await db.get(models.AnimeSeason, season_id): raise HTTPException(404, "季不存在")
    row = models.AnimeEpisode(season_id=season_id, episode_number=payload.episode_number, title=payload.title, feeling=payload.feeling)
    db.add(row); await db.commit(); await db.refresh(row); return {"id": row.id, "episode_number": row.episode_number, "title": row.title, "feeling": row.feeling}


@router.put("/anime/episodes/{episode_id}")
async def update_episode(episode_id: int, payload: EpisodePayload, login: LoginUser, db: Db):
    row = await db.get(models.AnimeEpisode, episode_id)
    if not row: raise HTTPException(404, "集数不存在")
    row.episode_number, row.title, row.feeling = payload.episode_number, payload.title, payload.feeling
    await db.commit(); return {"id": row.id, "episode_number": row.episode_number, "title": row.title, "feeling": row.feeling}


@router.post("/anime/{work_id}/images")
async def upload_anime_image(work_id: int, login: LoginUser, db: Db, file: UploadFile = File(...), episode_id: int | None = Form(None)):
    if not await db.get(models.AnimeWork, work_id): raise HTTPException(404, "作品不存在")
    path, size = await storage.save("photo", file, allowed_exts=storage.IMAGE_EXTS, magic_check=True)
    image = models.AnimeImage(work_id=work_id, episode_id=episode_id, path=path, name=storage.original_name(file.filename or ""), size=size)
    db.add(image); await db.commit(); await db.refresh(image)
    return {"id": image.id, "name": image.name, "episode_id": image.episode_id, "url": f"/api/content/images/anime/{image.id}"}


@router.delete("/anime/{work_id}")
async def delete_anime(work_id: int, login: LoginUser, db: Db, show_private: ShowPrivate):
    row = _visible(await db.get(models.AnimeWork, work_id), show_private)
    imgs = (await db.scalars(select(models.AnimeImage).where(models.AnimeImage.work_id == row.id))).all()
    seasons = (await db.scalars(select(models.AnimeSeason).where(models.AnimeSeason.work_id == row.id))).all()
    season_ids = [s.id for s in seasons]
    if season_ids:
        await db.execute(delete(models.AnimeEpisode).where(models.AnimeEpisode.season_id.in_(season_ids)))
        await db.execute(delete(models.AnimeSeason).where(models.AnimeSeason.id.in_(season_ids)))
    await db.execute(delete(models.AnimeImage).where(models.AnimeImage.work_id == row.id))
    await db.delete(row); await db.commit()
    for image in imgs: storage.delete(image.path)
    return {"message": "删除成功"}


@router.get("/content/images/{kind}/{image_id}")
async def get_content_image(kind: str, image_id: int, db: Db, show_private: ShowPrivate):
    if kind == "character": image = await db.get(models.CharacterImage, image_id); parent = await db.get(models.CharacterProfile, image.character_id) if image else None
    elif kind == "anime": image = await db.get(models.AnimeImage, image_id); parent = await db.get(models.AnimeWork, image.work_id) if image else None
    else: raise HTTPException(404, "图片不存在")
    _visible(parent, show_private)
    target = storage.resolve_saved(image.path)
    if not target.is_file(): raise HTTPException(404, "图片文件不存在")
    return FileResponse(target, media_type=mimetypes.guess_type(str(target))[0] or "application/octet-stream")
