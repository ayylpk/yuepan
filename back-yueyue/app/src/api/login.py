"""登录/会话接口层(≈ LoginController):路径挂在 /api/auth 下,前端 stores/auth.ts 契约。

鉴权方案(9/15 拍板,不用 JWT):
  登录 → tools/session 建服务端会话 → sid 写进 HttpOnly cookie(yueyue_sid);
  之后浏览器自动带 cookie,服务端按 sid 查会话 —— 状态的唯一真源在服务器内存里。

文件名和你的其他 api 一样是"域"命名(login.py),URL 前缀用 auth,两者不冲突。
七个端点,成功一律 Result 信封;失败一律 HTTPException(前端拿 detail 弹提示)。
9/16 迁 async:Db 依赖换 SQLAlchemy 的 get_db,service 调用全部 await。
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config.settings import API_PREFIX, SESSION_COOKIE, SESSION_TTL_SECONDS
from app.common.result.result import Result
from app.common.schemas.user.login_request import LoginRequest
from app.common.schemas.user.password_update import PasswordUpdate
from app.common.schemas.user.private_unlock import PrivateUnlock
from app.common.schemas.user.username_update import UsernameUpdate
from app.database.engine import get_db
from app.src.service import user_service
from app.tools import session

router = APIRouter(prefix=f"{API_PREFIX}/auth", tags=["login"])

Db = Annotated[AsyncSession, Depends(get_db)]


@router.post("/login", response_model=Result[None])
async def Login(dto: LoginRequest, res: Response, db: Db):
    """校验账号密码 → 建会话 → Set-Cookie。密码错了 service 抛 401。"""
    row = await user_service.verify_login(db, dto.username, dto.password)
    sid = session.create_session(row.id, row.username)
    res.set_cookie(
        SESSION_COOKIE,
        sid,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,  # 前端 JS 读不到,防 XSS 偷会话
        samesite="lax",  # 站内跳转换请求带 cookie;第三方站点带不上
    )
    return Result[None].success(message="登录成功")


@router.post("/logout", response_model=Result[None])
def Logout(request: Request, res: Response):
    """服务端删会话 + 客户端抹 cookie,两头都清干净。"""
    session.destroy(request)
    res.delete_cookie(SESSION_COOKIE)
    return Result[None].success(message="已退出")


@router.get("/me", response_model=Result[dict])
def Me(request: Request):
    """问登录态:唯一不抛 401 的受保护接口 —— 没登录也正常答 logged_in=False,
    让前端路由闸门自己决定跳不跳登录页(401 会触发 http.ts 强制跳转,这里不该)。"""
    current = session.find(request)
    if current is None:
        return Result[dict].success(data={"logged_in": False})
    return Result[dict].success(
        data={
            "logged_in": True,
            "username": current["username"],
            "private": bool(current["private"]),
        }
    )


@router.post("/password", response_model=Result[None])
async def ChangePassword(dto: PasswordUpdate, db: Db, login_user: session.LoginUser):
    """改主密码(先验旧);改完不踢会话,当前浏览器继续在线。"""
    await user_service.change_password(db, login_user["user_id"], dto.old_password, dto.new_password)
    return Result[None].success(message="主密码已更新")


@router.post("/username", response_model=Result[None])
async def ChangeUsername(dto: UsernameUpdate, db: Db, login_user: session.LoginUser):
    """改用户名(也要验当前密码,敏感操作)。"""
    await user_service.change_username(db, login_user["user_id"], dto.new_username, dto.password)
    login_user["username"] = dto.new_username
    return Result[None].success(message="用户名已更新")


@router.post("/private/unlock", response_model=Result[None])
async def UnlockPrivate(dto: PrivateUnlock, db: Db, login_user: session.LoginUser):
    """第二道锁:验小屋私钥 → 点亮会话 private 标记(日记 role=1 从此可见)。"""
    await user_service.verify_private(db, login_user["user_id"], dto.password)
    login_user["private"] = True
    return Result[None].success(message="小屋已解锁")


@router.post("/private/lock", response_model=Result[None])
def LockPrivate(login_user: session.LoginUser):
    """手动落锁(关浏览器/会话到期也会自动回锁)。"""
    login_user["private"] = False
    return Result[None].success(message="小屋已上锁")


@router.post("/private/password", response_model=Result[None])
async def ChangePrivatePassword(dto: PasswordUpdate, db: Db, login_user: session.LoginUser):
    """换小屋锁芯(先验旧私钥)。"""
    await user_service.change_private_password(
        db, login_user["user_id"], dto.old_password, dto.new_password
    )
    return Result[None].success(message="小屋锁芯已换")
