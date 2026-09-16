"""代码浏览接口层(≈ @Controller /code):CodeView.vue 的四读 + 管理两写。

读端点公开(本站核心展示),reindex/pull 要登录 —— 这两个会动磁盘/动 git,
和小屋、写接口同一把锁(LoginUser)。query 参数名 repo/path 和前端 http.ts
调用逐字一致,CodeView 零改动直接对接。
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config.settings import API_PREFIX
from app.common.schemas.code.code_file_response import CodeFileResponse
from app.common.schemas.code.code_tree_response import CodeTreeResponse
from app.common.schemas.code.commit_info_response import CommitInfoResponse
from app.common.schemas.code.repo_info_response import RepoInfoResponse
from app.database.engine import get_db
from app.src.service import code_service
from app.tools.session import LoginUser

router = APIRouter(prefix=f"{API_PREFIX}/code", tags=["code"])

Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("/repos", response_model=list[RepoInfoResponse])
async def list_repos_api(db: Db):
    """白名单仓库条(CodeView 顶部 chip 行)。"""
    return await code_service.list_repos(db)


@router.get("/tree", response_model=CodeTreeResponse)
async def get_tree_api(
    repo: str,
    db: AsyncSession = Depends(get_db),
):
    """平铺文件列表 → 前端 buildTree() 拼树。"""
    return await code_service.get_tree(db, repo)


@router.get("/file", response_model=CodeFileResponse)
async def get_file_api(
    repo: str,
    path: str,
    db: AsyncSession = Depends(get_db),
):
    """jail 读盘:path = 相对项目根的 POSIX 路径。"""
    return await code_service.get_file(db, repo, path)


@router.get("/log", response_model=list[CommitInfoResponse])
async def get_log_api(
    repo: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    return await code_service.get_log(db, repo, limit)


@router.post("/reindex")
async def reindex_api(repo: str, db: Db, login_user: LoginUser):
    """整项目重建索引(也可走 CLI,见 tools/code_indexer.py)。"""
    count = await code_service.reindex(db, repo)
    return {"message": f"索引已重建:{count} 个文件"}


@router.post("/pull")
async def pull_api(repo: str, db: Db, login_user: LoginUser):
    """git pull --ff-only(只做快进,有分叉让 git 报错回来,不自动 rebase 冒险)。"""
    msg = await code_service.pull(db, repo)
    return {"message": msg}
