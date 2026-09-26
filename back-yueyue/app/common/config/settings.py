"""全局配置(Java 视角:@Configuration + application.yml 的常量部分)。

只放路径和全局参数,业务规则不进这里(那属于 service 层)。
9/16 结构整理:原来叫 config/config.py(包名撞文件名),改名 settings.py
(Django/FastAPI 社区惯例,≈ Spring 的 application.properties)。
"""
import os
from pathlib import Path

# settings.py 位于 app/common/config/:parents[2] 是 app/,parents[3] 是项目根
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# 磁盘资源唯一真相源:数据库文件、上传的照片/资料全都收在 <项目根>/resources/ 下。
# 9/16 之前真库埋在 app/database/resources/、根目录还摆着几个空壳目录,双真相源是
# 目录混乱的源头,现在全部归拢到这一棵树下(路径口径:相对 resources/ 的正斜杠路径)。
RESOURCES_DIR = PROJECT_ROOT / "resources"

# "在线看代码"挂载仓库的根目录(9/17 口径统一:project.path 起这天后入库只存
# 相对这里的相对路径,如 "yueyue/front-yueyue" —— 和照片相对 resources/ 同一姿势)。
# 换机器/挪仓库存放地:改这一行(或设环境变量 REPOS_DIR),DB 里的行一行都不用动。
REPOS_DIR = Path(os.getenv("REPOS_DIR", "F:/code/project"))

# 允许的跨域来源(逗号分隔)。开发期 vite dev 走代理=同源,用不上这层;
# 部署时若前端域名直连本服务(不反代 /api),设 CORS_ORIGINS=https://实际前端源。
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
]

# 所有接口的公共前缀
API_PREFIX = "/api"

# 会话(登录态)参数:实现在 tools/session.py(服务端内存会话,不用 JWT)
SESSION_COOKIE = "yueyue_sid"
SESSION_TTL_SECONDS = 7 * 24 * 3600
