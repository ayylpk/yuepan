"""应用装配(Java 视角:@SpringBootApplication + 启动钩子)。

runApp.py 负责把这里的 app 跑起来;新模块接入 = 建 api/xxx.py + 在这 include。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.common.Result.result import Result
from app.src.api import code, diary, login, project, tech, user
from app.tools.db import init_db


@asynccontextmanager
async def lifespan(application: FastAPI):
    await init_db()  # 启动建表 + 空表塞 admin 种子(幂等),≈ ApplicationRunner
    yield


app = FastAPI(title="月畔小站 API", version="0.1.0", lifespan=lifespan)

# 开发期:vite dev(5173) 走代理时是同源,这层是给直连 8000 调试兜底的
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,  # HttpOnly session cookie 跨域必须开这个
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(code.router)
app.include_router(diary.router)
app.include_router(login.router)
app.include_router(project.router)
app.include_router(tech.router)
app.include_router(user.router)


@app.get("/api/health", response_model=Result[dict])
def health():
    """探活也走统一信封,前端处理口径一致。"""
    return Result[dict].success(data={"service": "yueyue-back"})
