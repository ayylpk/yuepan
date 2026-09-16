"""改技术栈名入参(PATCH 语义,同 DiaryUpdate 口径)。

改名也要过大小写查重:撞了别的记录(比如已有 "Vue" 你要把 "js" 改成 "vue")给 409,
不静默合并 —— 改名是显式动作,合并该由人拍板。
"""
from typing import Annotated, Optional

from pydantic import BaseModel, Field


class TechUpdate(BaseModel):
    name: Optional[Annotated[str, Field(min_length=1, max_length=50)]] = None
