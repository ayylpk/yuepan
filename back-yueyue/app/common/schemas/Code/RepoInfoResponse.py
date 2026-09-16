"""代码白名单仓库信息(对齐 types.ts 的 RepoInfo,CodeView 仓库条用)。

name = 项目的 repo 列(空则回退 name);exists=false 代表项目挂了 path 但目录没了,
前端把 chip 置灰,不算报错 —— 你的站你在本机跑,目录搬家很正常。
"""
from pydantic import BaseModel


class RepoInfoResponse(BaseModel):
    name: str
    desc: str = ""
    exists: bool = False
    branch: str = ""
    last_commit: str = ""
