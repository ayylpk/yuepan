# 月畔小站 后端镜像(FastAPI + uvicorn + SQLite + 磁盘文件存储)
#
# 三条不能违反的约束(依据见 CI-CD部署规划.md 第 1 章):
#  1) WORKDIR 必须是 /app。settings.RESOURCES_DIR = PROJECT_ROOT/"resources",
#     而该路径不可用环境变量覆盖 → 数据卷只能挂 /app/resources。
#     (目录层级:COPY 后是 /app/app/common/config/settings.py,parents[3] 正好是 /app)
#  2) 必须 --workers 1。会话是进程内字典(back-yueyue/app/tools/session.py),
#     多 worker 会互相不认登录态;这不是漏写,是刻意选择。
#  3) 必须装 git。code_service 会跑 `git ls-files` / `git log` / `git pull`
#     支撑「在线看代码」;不装的话该页会静默降级成空历史(代码里有兜底,但功能就废了)。
FROM python:3.12-slim

# uv:仓库里有 uv.lock,按锁文件装依赖,可复现且比 pip 快
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

# git 是「在线看代码」的硬依赖;ca-certificates 供 git 走 https 拉取
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# 先只拷依赖声明:改业务代码不会让依赖层缓存失效
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# 再拷应用本体
COPY app ./app
COPY runApp.py ./

# resources/(SQLite 库 + 上传的照片与资料原件)是运行期数据,
# 这一层只是占位,真正的内容由 compose 挂载覆盖(否则每次部署数据清零)
RUN mkdir -p /app/resources

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"

# 用 python -m 而不是 uvicorn 控制台脚本:cwd 会进 sys.path,`app` 包才找得到
CMD ["python", "-m", "uvicorn", "app.src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
