"""人物志与动漫展示 API。图片复用 resources/photo 存储，权限继承父条目。"""
import mimetypes
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
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


def _base(row):
    return {"id": row.id, "visibility": "private" if row.role else "public", "created_at": row.created_at, "updated_at": getattr(row, "updated_at", row.created_at)}


async def _image_url(kind: str, image_id: int, db: AsyncSession):
    return f"/api/content/images/{kind}/{image_id}"


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
    rows = (await db.scalars(select(models.CharacterProfile).order_by(models.CharacterProfile.updated_at.desc()))).all()
    return [await _character_data(r, db) for r in rows if r.role == 0 or show_private]


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
    rows = (await db.scalars(select(models.AnimeWork).order_by(models.AnimeWork.updated_at.desc()))).all()
    return [await _anime_data(r, db) for r in rows if r.role == 0 or show_private]


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
