"""代码浏览业务层(≈ @Service):/api/code/* 四读的规则 + reindex/pull 两写。

数据口径(和方案定稿一致):
  - 一切以"项目 + path"为事实源:repos=挂了 path 的项目投影,
    tree=files 索引表,log/pull=对 path 目录跑 git 子命令;
  - 目录树是平铺 path 派生的,读文件 = project.path + 相对路径 → 磁盘,
    中间隔一道 jail(tools/storage.jail,全站共用),这是本模块唯一的安全生命线;
  - tree 空索引时顺手重建一次(git ls-files 毫秒级),
    免得"项目刚挂上、还没点 reindex"的冷启动体验是空页。
"""
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas.code.code_file_response import CodeFileResponse
from app.common.schemas.code.code_tree_response import CodeTreeResponse
from app.common.schemas.code.commit_info_response import CommitInfoResponse
from app.common.schemas.code.repo_info_response import RepoInfoResponse
from app.database.models import Project
from app.src.repositories import code_repository, project_repository
from app.tools.code_indexer import MAX_FILE_BYTES, git_pull, git_run, reindex_project
# 路径生命线 9/16 抽到 tools/storage.py 全站共用,这里只是换个本地小名继续用;
# repo_root:DB 相对路径 → 本机仓库目录(9/17 起 project.path 也只存相对)
from app.tools.storage import jail as _jail, repo_root as _repo_root

_BINARY_SNIFF_BYTES = 8192


async def _require_project(db: AsyncSession, repo: str) -> Project:
    project = await project_repository.select_by_repo_name(db, repo)
    if project is None or not project.path:
        raise HTTPException(status_code=404, detail=f"仓库「{repo}」不存在或没挂本机目录")
    return project


def _require_root(project: Project) -> Path:
    root = _repo_root(project.path)
    if not root.is_dir():
        raise HTTPException(status_code=404, detail=f"本机目录不存在:{root}")
    return root


async def list_repos(db: AsyncSession) -> list[RepoInfoResponse]:
    """白名单投影:path 非空的项目;branch/last_commit 现场问 git(仓库数量小,够用)。"""
    out: list[RepoInfoResponse] = []
    for p in await project_repository.select_all_with_path(db):
        root = _repo_root(p.path)
        exists = root.is_dir()
        out.append(
            RepoInfoResponse(
                name=p.repo or p.name,
                desc=p.description,
                exists=exists,
                branch=(git_run(root, "rev-parse", "--abbrev-ref", "HEAD") or "").strip() if exists else "",
                last_commit=(git_run(root, "log", "-1", "--format=%h %s") or "").strip() if exists else "",
            )
        )
    return out


async def get_tree(db: AsyncSession, repo: str) -> CodeTreeResponse:
    project = await _require_project(db, repo)
    rows = await code_repository.select_paths(db, project.id)
    if not rows:
        # 冷启动顺手建一次;目录没了就明确报出来,别静默给空树让人以为索引坏了
        try:
            await reindex_project(db, project)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        rows = await code_repository.select_paths(db, project.id)
    root = _repo_root(project.path)
    branch = (git_run(root, "rev-parse", "--abbrev-ref", "HEAD") or "").strip()
    files = [r.path for r in rows]
    return CodeTreeResponse(branch=branch, count=len(files), files=files)


async def get_file(db: AsyncSession, repo: str, path: str) -> CodeFileResponse:
    project = await _require_project(db, repo)
    target = _jail(_require_root(project), path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    size = target.stat().st_size
    if size > MAX_FILE_BYTES:
        raise HTTPException(status_code=400, detail="文件超过 2MB,不提供预览")
    with target.open("rb") as fh:
        if b"\x00" in fh.read(_BINARY_SNIFF_BYTES):
            raise HTTPException(status_code=400, detail="二进制文件,不预览")
    # errors=replace:个别文件混进坏字节就当乱码看,不该整个请求 500
    content = target.read_text(encoding="utf-8", errors="replace")
    return CodeFileResponse(path=path.replace("\\", "/"), content=content, size=size)


async def get_log(db: AsyncSession, repo: str, limit: int = 50) -> list[CommitInfoResponse]:
    limit = max(1, min(int(limit or 50), 100))
    root = _require_root(await _require_project(db, repo))
    # \x1f(单元分隔符)拼字段:commit 信息里不会出现,比普通分隔符稳
    out = git_run(
        root, "log", f"-{limit}", "--format=%h\x1f%s\x1f%an\x1f%ar"
    )
    if out is None:
        return []  # 没装 git / 非 git 目录:历史 tab 空着,不算错
    commits: list[CommitInfoResponse] = []
    for line in out.splitlines():
        parts = line.split("\x1f")
        if len(parts) == 4:
            commits.append(
                CommitInfoResponse(hash=parts[0], subject=parts[1], author=parts[2], ago=parts[3])
            )
    return commits


async def reindex(db: AsyncSession, repo: str) -> int:
    project = await _require_project(db, repo)
    try:
        return await reindex_project(db, project)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


async def pull(db: AsyncSession, repo: str) -> str:
    project = await _require_project(db, repo)
    root = _require_root(project)
    ok, msg = git_pull(root)
    if not ok:
        raise HTTPException(status_code=400, detail=f"git pull 失败:{msg}")
    return msg
