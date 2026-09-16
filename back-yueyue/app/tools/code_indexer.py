"""代码索引器(≈ 一次性 batch job):扫本机目录 → files 表整项目重建。

一个函数两个壳(确定性逻辑用代码,不做成花活):
  CLI  : uv run python -m app.tools.code_indexer --all
         uv run python -m app.tools.code_indexer --project 1 [--pull]
  API  : POST /api/code/reindex?repo=xxx(登录)→ reindex_project()
         POST /api/code/pull?repo=xxx(登录)→ git_pull()

扫盘策略:
  1. 有 .git → `git ls-files`:天然尊重 .gitignore,比任何手写黑名单都准;
  2. 没 git → os.walk 兜底,黑名单目录剪枝(node_modules/dist/__pycache__...);
  3. 单文件 > 2MB 一律不进索引(构建产物/锁文件大户),打开侧还有二次上限。

git 子进程铁律:argv 列表传参 + 固定 cwd(-C)+ timeout,**永不开 shell**
(≈ ProcessBuilder 不是 Runtime.exec(String) —— 不给命令行注入留口子)。
"""
import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import AsyncSessionLocal, Project, create_tables
from app.src.repositories import code_repository, project_repository

MAX_FILE_BYTES = 2 * 1024 * 1024

# 仅 walk 兜底用;git 仓库以 .gitignore 为准
IGNORE_DIRS = {
    ".git", "node_modules", "dist", "build", "target", "out",
    "__pycache__", ".venv", "venv", ".idea", ".vscode",
    ".next", ".nuxt", ".cache", "coverage",
}

# walk 兜底的文件黑名单:本机目录可能藏着密钥,一律不进公开树。
# git 仓库**不吃这份清单** —— tracked 文件是仓库作者自己选择公开的(.env.example 之类),
# gitignore 已经挡掉 .env.local,尊重仓库意图即可;walk 没有这层意图可参考,保守来。
WALK_SKIP_PREFIX = (".env",)
WALK_SKIP_SUFFIX = (".pem", ".key", ".p12", ".pfx")
WALK_SKIP_NAMES = {"id_rsa", "id_ed25519", "id_ecdsa"}


def git_run(root: Path, *args: str, timeout: int = 30) -> str | None:
    """跑一条 git 命令,成功返回 stdout(utf-8),非零/超时/git 没装返回 None。"""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def git_pull(root: Path) -> tuple[bool, str]:
    """--ff-only:只做快进合并,有分叉/冲突直接失败回显 git 原话,不自动 rebase 冒险。"""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "pull", "--ff-only"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False, "git pull 超时或 git 不可用"
    tail = (result.stdout or result.stderr or "").strip()
    return result.returncode == 0, tail[-500:] or "(无输出)"


def _row_from_rel(root: Path, rel: str) -> dict[str, Any] | None:
    """相对路径 → 索引行;文件不存在(索引里有实际已删)/超限 → None 跳过。"""
    fp = root / rel
    try:
        size = fp.stat().st_size
    except OSError:
        return None
    if size > MAX_FILE_BYTES:
        return None
    fn = rel.rsplit("/", 1)[-1]
    ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
    return {"path": rel, "type": ext[:20], "size": size}


def git_files(root: Path) -> list[str] | None:
    """git 仓库 → ls-files 平铺路径(正斜杠);非 git 返回 None 交给 walk。
    -z 用 NUL 分隔,免俗成引号/转义问题;core.quotepath=false 让中文路径原样输出。
    """
    if not (root / ".git").exists():
        return None
    out = git_run(root, "-c", "core.quotepath=false", "ls-files", "-z", timeout=30)
    if out is None:
        return None
    return [p for p in out.split("\0") if p]


def walk_files(root: Path) -> list[str]:
    """无 git 兜底:os.walk + 目录黑名单剪枝 + 密钥文件排除,路径统一正斜杠。"""
    rels: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for name in filenames:
            if (
                name.startswith(WALK_SKIP_PREFIX)
                or name.endswith(WALK_SKIP_SUFFIX)
                or name in WALK_SKIP_NAMES
            ):
                continue
            rel = Path(dirpath, name).relative_to(root).as_posix()
            rels.append(rel)
    return rels


async def reindex_project(db: AsyncSession, project: Project) -> int:
    """整项目重建索引,返回条数。目录不存在抛 ValueError(api 层翻译成 400)。"""
    root = Path(project.path) if project.path else None
    if root is None or not root.is_dir():
        raise ValueError(f"本机目录不存在:{project.path or '(未填 path)'}")
    git = git_files(root)
    rels = git if git is not None else walk_files(root)
    rows = [row for row in (_row_from_rel(root, r) for r in rels) if row is not None]
    return await code_repository.rebuild_index(db, project.id, rows)


async def reindex_all(db: AsyncSession) -> list[str]:
    """--all:所有挂了 path 的项目逐个重建;失败的记录原因继续跑(批量任务不连坐)。"""
    report: list[str] = []
    for project in await project_repository.select_all_with_path(db):
        name = project.repo or project.name
        try:
            count = await reindex_project(db, project)
            report.append(f"{name}: {count} 个文件")
        except ValueError as exc:
            report.append(f"{name}: 跳过({exc})")
    return report


async def _cli(args: argparse.Namespace) -> None:
    await create_tables()
    async with AsyncSessionLocal() as db:
        if args.project is not None:
            project = await project_repository.select_by_id(db, args.project)
            if project is None:
                print(f"[x] 项目 id={args.project} 不存在")
                return
            if args.pull:
                ok, msg = git_pull(Path(project.path))
                print(f"{'[ok]' if ok else '[x]'} git pull: {msg}")
            try:
                print(f"[ok] 重建索引 {await reindex_project(db, project)} 个文件")
            except ValueError as exc:
                print(f"[x] {exc}")
        else:
            for line in await reindex_all(db):
                print(f"[ok] {line}")


def main() -> None:
    # Windows 控制台默认 GBK,中文项目名/提交主题会炸 UnicodeEncodeError,统一 utf-8
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="yueyue 代码索引器(整项目重建)")
    parser.add_argument("--project", type=int, help="只重建指定项目 id 的索引")
    parser.add_argument("--all", action="store_true", help="重建所有挂了 path 的项目(默认)")
    parser.add_argument("--pull", action="store_true", help="配合 --project:先 git pull --ff-only")
    args = parser.parse_args()
    asyncio.run(_cli(args))


if __name__ == "__main__":
    main()
