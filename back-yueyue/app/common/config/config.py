"""全局配置(Java 视角:@Configuration + application.yml 的常量部分)。

只放路径和全局参数,业务规则不进这里(那属于 service 层)。
"""
from pathlib import Path

# config.py 位于 app/common/config/,parents[2] 就是 app/
APP_DIR = Path(__file__).resolve().parents[2]

# 9/16 迁 SQLAlchemy 后全站单一库文件,路径由 database/db.py 自己拼(app/database/resources/database/yueyue.db);
# 原来这里的 DIARY_DB/USER_DB 常量已废弃删除,免得后人拿旧路径开出第二个库

# 所有接口的公共前缀
API_PREFIX = "/api"

# 会话(登录态)参数:实现在 tools/session.py(服务端内存会话,不用 JWT)
SESSION_COOKIE = "yueyue_sid"
SESSION_TTL_SECONDS = 7 * 24 * 3600
