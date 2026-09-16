"""建号入参(≈ 注册接口的 @RequestBody DTO)。

站内目前只有一个账号:种子在 tools/db.init_db 直插,不走这个 DTO;
它是给你以后加"注册/导入"接口备着的,字段先按你的定义立好规矩。

两处对原稿的修正(都是 pydantic v2 的坑):
- datetime 的默认值要写 default_factory —— 写 datetime.now() 会在 import 时
  执行一次,之后所有对象的 created_at 都是"服务启动那一刻";
- 默认值写进 Field(default=...) 即可,不用 Optional 包(包了反而不自动给 None)。
"""
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: Annotated[str, Field(min_length=1, max_length=32)]
    password: Annotated[str, Field(min_length=6, max_length=64)]
    email: Annotated[str, Field(default="")]
    phone: Annotated[str, Field(default="")]
    QQ: Annotated[str, Field(default="")]
    created_at: Annotated[datetime, Field(default_factory=datetime.now)]
