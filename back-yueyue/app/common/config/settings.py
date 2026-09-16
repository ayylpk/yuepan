"""全局配置(Java 视角:@Configuration + application.yml 的常量部分)。

只放路径和全局参数,业务规则不进这里(那属于 service 层)。
9/16 结构整理:原来叫 config/config.py(包名撞文件名),改名 settings.py
(Django/FastAPI 社区惯例,≈ Spring 的 application.properties)。
"""
from pathlib import Path

# settings.py 位于 app/common/config/:parents[2] 是 app/,parents[3] 是项目根
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# 磁盘资源唯一真相源:数据库文件、上传的照片/资料全都收在 <项目根>/resources/ 下。
# 9/16 之前真库埋在 app/database/resources/、根目录还摆着几个空壳目录,双真相源是
# 目录混乱的源头,现在全部归拢到这一棵树下(路径口径:相对 resources/ 的正斜杠路径)。
RESOURCES_DIR = PROJECT_ROOT / "resources"

# 所有接口的公共前缀
API_PREFIX = "/api"

# 会话(登录态)参数:实现在 tools/session.py(服务端内存会话,不用 JWT)
SESSION_COOKIE = "yueyue_sid"
SESSION_TTL_SECONDS = 7 * 24 * 3600
