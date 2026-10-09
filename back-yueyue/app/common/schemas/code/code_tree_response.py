"""文件树出参(对齐 CodeView 的 RepoTree:{branch, count, files: string[]})。

刻意的**平铺**设计:files 只装 "src/api/http.ts" 这样的相对路径,
嵌套树由前端 buildTree() 现拼(CodeView.vue 已写好)——
目录层级是派生状态不落库,这里自然也不回目录对象。
"""
from pydantic import BaseModel


class CodeTreeResponse(BaseModel):
    branch: str = ""
    count: int = 0
    files: list[str] = []
