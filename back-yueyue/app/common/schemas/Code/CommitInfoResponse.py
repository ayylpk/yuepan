"""提交记录出参(对齐 types.ts 的 CommitInfo,CodeView 历史 tab 用)。

hash 用短格式(%h 7位);ago 直接要 git 的相对日期(%ar,"3 days ago" 原样,
前端没做本地化,个人站先不翻译)。
"""
from pydantic import BaseModel


class CommitInfoResponse(BaseModel):
    hash: str
    subject: str
    author: str
    ago: str
