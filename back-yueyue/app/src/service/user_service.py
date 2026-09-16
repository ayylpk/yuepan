"""用户业务层(≈ @Service):校验、组合、抛 HTTPException 都在这层,api 层不碰 SQL。

9/16 随 diary 迁 SQLAlchemy async:函数名原样保留(user/verify_login/...),
入参 conn: sqlite3.Connection → db: AsyncSession,行访问 row["xx"] → row.xx。

密码铁律:库里只有哈希,明文只存在于"请求进来 → security 比对"这一瞬间,
比对函数统一收口在这层 —— 换/验/种三条路共用一把尺子。
"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas.user.UserResponse import UserResponse
from app.common.schemas.user.UserUpdate import UserUpdate
from app.database.db import User
from app.src.repositories import user_repository
from app.tools.security import hash_password, verify_password

# PUT /api/user/ 允许改的字段:{前端/DTO 字段名 → 表列名}。
# password 不在列内:改密必须走 /api/auth/password,要先验旧密码。
# QQ 单独映射是因为前端口径大写、表列小写(setattr 只认列名)。
UPDATABLE_FIELDS = {"username": "username", "email": "email", "QQ": "qq", "phone": "phone"}


def _to_response(user: User) -> UserResponse:
    """库行 → 出参:哈希字段打星再交给 validate(9/16 手改口径保留)。

    UserResponse 本来就没接这两个字段(pydantic 会把 schema 外的键丢掉,双保险);
    显式打星是防"以后谁给 VO 加了 password 槽" —— 那也漏出去是星号,不是哈希。
    """
    data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "QQ": user.qq,
        "created_at": user.created_at,
        "password": "******",
        "private_password": "******",
    }
    return UserResponse.model_validate(data)


async def user(db: AsyncSession, user_id: int) -> UserResponse:
    """查用户资料(原稿函数名保留)。查不到 404:站里就一个号,不区分不泄漏。"""
    row = await user_repository.select_by_id(db, user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return _to_response(row)


async def verify_login(db: AsyncSession, username: str, password: str) -> User:
    """登录校验:成功返回整行(给 api 建会话用),失败 401。

    话术故意模糊("用户名或密码不对"):不告诉对方是哪个错了,少给猜号线索。
    """
    row = await user_repository.select_by_username(db, username)
    if row is None or not verify_password(password, row.password):
        raise HTTPException(status_code=401, detail="用户名或密码不对")
    return row


async def update_user(db: AsyncSession, user_id: int, dto: UserUpdate) -> UserResponse:
    """改资料:exclude_unset=只改真传了的字段;username 撞 UNIQUE 提前给个体面 409。"""
    dumped = dto.model_dump(exclude_unset=True)
    fields = {
        column: dumped[vo]
        for vo, column in UPDATABLE_FIELDS.items()
        if vo in dumped
    }
    if "username" in fields:
        if await user_repository.select_by_username(db, fields["username"]) is not None:
            raise HTTPException(status_code=409, detail="这个用户名已经被占了")
    await user_repository.update_fields(db, user_id, fields)
    return await user(db, user_id)


async def change_password(db: AsyncSession, user_id: int, old: str, new: str) -> None:
    """换主密码:先验旧的,再把新哈希写进去。"""
    await _require_password(db, user_id, old)
    await user_repository.update_fields(db, user_id, {"password": hash_password(new)})


async def change_username(db: AsyncSession, user_id: int, username: str, password: str) -> None:
    """换用户名:也要验当前密码(改名=换登录凭证,敏感操作)。"""
    await _require_password(db, user_id, password)
    if await user_repository.select_by_username(db, username) is not None:
        raise HTTPException(status_code=409, detail="这个用户名已经被占了")
    await user_repository.update_fields(db, user_id, {"username": username})


async def verify_private(db: AsyncSession, user_id: int, password: str) -> None:
    """验小屋钥匙(私钥):不对就 400,api 层拿到"验过了"才点亮会话标记。"""
    row = await user_repository.select_by_id(db, user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not verify_password(password, row.private_password):
        raise HTTPException(status_code=400, detail="解锁密码不对")


async def change_private_password(db: AsyncSession, user_id: int, old: str, new: str) -> None:
    """换小屋锁芯:先验旧私钥。"""
    await verify_private(db, user_id, old)
    await user_repository.update_fields(db, user_id, {"private_password": hash_password(new)})


async def _require_password(db: AsyncSession, user_id: int, password: str) -> None:
    row = await user_repository.select_by_id(db, user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not verify_password(password, row.password):
        raise HTTPException(status_code=401, detail="当前密码不对")
