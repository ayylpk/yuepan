"""修改日记的入参 DTO:全部字段可选(PATCH 语义的 PUT)。

不传的字段=不改;service 用 model_dump(exclude_unset=True) 区分
"没传" 和 "传了 null/空串",支持只改 role 这种单字段操作。
"""
from typing import Annotated, Optional

from pydantic import BaseModel, Field


class DiaryUpdate(BaseModel):
    title: Optional[Annotated[str, Field(min_length=1, max_length=120)]] = None
    content: Optional[str] = None
    # role 明确支持修改:0=摆回公开, 1=收进小屋
    role: Optional[Annotated[int, Field(ge=0, le=1, description="0=正常 1=隐私,可改")]] = None
