"""服务端内存会话(Java 视角:Tomcat 的 HttpSession + JSESSIONID,只是自己实现)。

流程:登录成功 → 生成随机 sid 存进字典,同时把 sid 写进 HttpOnly cookie;
以后每个请求浏览器自动带 cookie → 按 sid 查回会话。前端 JS 读不到 cookie
(HttpOnly),也就偷不走登录态;退出/过期就是字典里删掉,没有第二份真相。

两个刻意的取舍(个人站,别过度设计):
- 存内存不存库:重启服务会掉登录,重新登录一次即可,数据零丢失;
- "小屋解锁标记"也挂在会话上(private 字段),关浏览器/到期自动回锁,
  正好当第二道锁的超时。
"""
import secrets
import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from app.common.config.settings import SESSION_COOKIE, SESSION_TTL_SECONDS

# sid → 会话字典。进程级单例(≈ 静态 ConcurrentHashMap),只放得下几个键。
_SESSIONS: dict[str, dict] = {}


def create_session(user_id: int, username: str) -> str:
    """开一场会话,返回 sid(≈ request.getSession(true) 后拿 id)。"""
    sid = secrets.token_urlsafe(32)  # 32 字节随机数,猜不到
    _SESSIONS[sid] = {
        "user_id": user_id,
        "username": username,
        "private": False,  # 小屋解锁标记,新会话默认锁着
        "expires": time.time() + SESSION_TTL_SECONDS,
    }
    return sid


def find(request: Request) -> dict | None:
    """按 cookie 里的 sid 找会话;过期就顺手清掉(惰性回收,个人站量小够用)。"""
    now = time.time()
    for sid in [k for k, v in _SESSIONS.items() if v["expires"] < now]:
        del _SESSIONS[sid]
    sid = request.cookies.get(SESSION_COOKIE)
    if not sid:
        return None
    session = _SESSIONS.get(sid)
    if session and session["expires"] < now:
        del _SESSIONS[sid]
        return None
    return session


def destroy(request: Request) -> None:
    """退出登录 = 服务端删会话(≈ session.invalidate())。"""
    sid = request.cookies.get(SESSION_COOKIE)
    if sid:
        _SESSIONS.pop(sid, None)


def require_login(request: Request) -> dict:
    """依赖:没登录直接 401(前端 http.ts 见 401 自动轰回登录页)。"""
    session = find(request)
    if not session:
        raise HTTPException(status_code=401, detail="登录已过期,请重新登录")
    return session


# 给 api 层用的参数类型别名:LoginUser = 当前会话,PrivateOn = 小屋是否解锁
LoginUser = Annotated[dict, Depends(require_login)]


def private_unlocked(request: Request) -> bool:
    """日记可见性用:解锁小屋才看得到 role=1,没登录自然是 False。"""
    session = find(request)
    return bool(session and session["private"])


ShowPrivate = Annotated[bool, Depends(private_unlocked)]
