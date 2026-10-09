"""单文件内容出参(对齐 CodeView 的 CodeFile:{path, content, size})。

path 回传的是**规范化后的相对路径**(正斜杠),不是原样回显入参;
content 只装文本 —— 二进制/超大在 service 层就 400 掉了,不会到这。
"""
from pydantic import BaseModel


class CodeFileResponse(BaseModel):
    path: str
    content: str
    size: int
