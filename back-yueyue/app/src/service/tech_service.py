"""技术栈业务层(≈ @Service):大小写不敏感的**唯一实现处**。

规则(需求原话"匹配的时候不区分大小写")全收在这:
  1. normalize():strip + lower,原样进 name、归一化进 name_key;
  2. create 撞 key 不报错 → 幂等返回已有记录(弹窗输入"vue"命中"Vue");
  3. rename 撞 key 才 409(显式动作不静默合并);
  4. delete 有引用 409 带占用数;
  5. resolve_names():给项目弹窗用 —— 一批名字,命中即绑、未建则建。
project_service 不许自己 lower(),都调这里,免得两处尺子不一样。
"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas.Tech.TechCreate import TechCreate
from app.common.schemas.Tech.TechResponse import TechResponse
from app.common.schemas.Tech.TechUpdate import TechUpdate
from app.database.db import TechStack
from app.src.repositories import tech_repository


def normalize(raw: str) -> tuple[str, str]:
    """原始输入 → (展示名, 归一化键)。全空给 400。"""
    name = raw.strip()
    if not name:
        raise HTTPException(status_code=400, detail="技术栈名称不能为空")
    return name, name.lower()


def _to_response(tech: TechStack, ref_count: int = 0) -> TechResponse:
    return TechResponse.model_validate(
        {
            "id": tech.id,
            "name": tech.name,
            "ref_count": ref_count,
            "created_at": tech.created_at,
        }
    )


async def create(db: AsyncSession, dto: TechCreate) -> TechResponse:
    """幂等新增:命中已有(任意大小写形态)直接返回那条,不产生重复记录。"""
    name, key = normalize(dto.name)
    hit = await tech_repository.select_by_key(db, key)
    if hit is not None:
        ref = await tech_repository.count_refs(db, hit.id)
        return _to_response(hit, ref)
    tech = await tech_repository.insert(db, name, key)
    return _to_response(tech, 0)


async def page(db: AsyncSession, page_no: int, page_size: int, keyword: str | None):
    key_kw = keyword.strip().lower() if keyword and keyword.strip() else None
    total = await tech_repository.count_all(db, key_kw)
    rows = await tech_repository.select_list(db, key_kw, page_no, page_size)
    return total, [_to_response(tech, ref) for tech, ref in rows]


async def list_all(db: AsyncSession) -> list[TechResponse]:
    """弹窗数据源:字典表量小,一次全给(前端做本地过滤)。"""
    rows = await tech_repository.select_list(db)
    return [_to_response(tech, ref) for tech, ref in rows]


async def update(db: AsyncSession, tech_id: int, dto: TechUpdate) -> TechResponse:
    tech = await tech_repository.select_by_id(db, tech_id)
    if tech is None:
        raise HTTPException(status_code=404, detail="技术栈不存在")
    dumped = dto.model_dump(exclude_unset=True)
    if "name" in dumped:
        name, key = normalize(dumped["name"])
        clash = await tech_repository.select_by_key(db, key)
        if clash is not None and clash.id != tech.id:
            raise HTTPException(
                status_code=409,
                detail=f"已有同名技术栈「{clash.name}」(大小写不敏感),要合并请改绑项目后删旧条目",
            )
        tech.name = name
        tech.name_key = key
        await db.commit()
        await db.refresh(tech)
    ref = await tech_repository.count_refs(db, tech.id)
    return _to_response(tech, ref)


async def delete(db: AsyncSession, tech_id: int) -> None:
    tech = await tech_repository.select_by_id(db, tech_id)
    if tech is None:
        raise HTTPException(status_code=404, detail="技术栈不存在")
    ref = await tech_repository.count_refs(db, tech_id)
    if ref > 0:
        raise HTTPException(status_code=409, detail=f"还有 {ref} 个项目在用,先去项目里解绑")
    await tech_repository.delete(db, tech)


async def resolve_names(db: AsyncSession, names: list[str]) -> list[TechStack]:
    """弹窗匹配核心:一批手输/选出的名字 → TechStack 行(命中即取,未建则建)。

    同一批里的重复(含大小写变体)按 key 去重,只建一条。
    返回顺序按输入顺序;给 project_service 建绑定用。
    """
    resolved: list[TechStack] = []
    seen: set[str] = set()
    for raw in names:
        name, key = normalize(raw)
        if key in seen:
            continue
        seen.add(key)
        hit = await tech_repository.select_by_key(db, key)
        resolved.append(hit if hit is not None else await tech_repository.insert(db, name, key))
    return resolved
