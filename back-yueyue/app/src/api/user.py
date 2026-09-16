"""用户资料接口层(≈ @RestController /user)。

9/16 迁 async:连接换成 database/db.py 的 get_db(全站一个 yueyue.db,
不再按域分 user.db/diary.db);函数名保持你的 PascalCase 风格。
直接返回 UserResponse 不套 Result 的口径不变 —— 前端 http.ts
对"有 code 拆信封、没 code 原样过"两种都兼容。
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config.config import API_PREFIX
from app.common.schemas.user.UserResponse import UserResponse
from app.common.schemas.user.UserUpdate import UserUpdate
from app.database.db import get_db
from app.src.service import user_service
from app.tools.session import LoginUser

router = APIRouter(prefix=f"{API_PREFIX}/user", tags=["user"])

Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("/")
async def GetUser(db: Db, login_user: LoginUser) -> UserResponse:
    """查当前登录用户的资料(改的是 login_user["user_id"],不是任选 id)。"""
    return await user_service.user(db, login_user["user_id"])


@router.put("/")
async def UpdateUser(dto: UserUpdate, db: Db, login_user: LoginUser) -> UserResponse:
    """改资料:PATCH 语义,只动传了的字段;密码不在这改(走 /api/auth/password)。"""
    return await user_service.update_user(db, login_user["user_id"], dto)
