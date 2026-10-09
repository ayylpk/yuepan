# 月畔小站 · CI/CD 部署规划（服务器 + Docker + dist 静态）

> 日期：2026-10-09
> 你的形态：**自有服务器 + Docker + dist 静态文件**
> 本文只做规划，**不写实现、不改代码**（按你的要求）。

---

## 0. 先回答你问的两件事

### 0.1 CI / CD 分别指什么

| 缩写 | 全称 | 干什么 | 部署吗 |
|---|---|---|---|
| **CI** | Continuous Integration 持续集成 | 每次 push / 提 PR 自动跑「构建 + 测试」，保证主干随时可用 | ❌ 不部署 |
| **CD** | Continuous **Delivery** 持续交付 | CI 绿了自动打包出可部署产物，**上线那一下由人点** | 半自动 |
| **CD** | Continuous **Deployment** 持续部署 | 连上线也自动，push 到 main 就直接发到服务器 | ✅ 全自动 |

落到你这个站：

- **CI** = 前端 `npm run build`（内含 `vue-tsc` 类型检查）+ 后端 `smoke_test.py` 43 条冒烟
- **CD** = 把前后端打成镜像 → 推到镜像仓库 → 服务器拉下来重启容器

### 0.2 token 还是 cookie

**不需要 token，你现在用的 HttpOnly Cookie 就是更安全的那个。** 依据（`back-yueyue/app/src/api/login.py:36`）：

```python
res.set_cookie(SESSION_COOKIE, sid, max_age=SESSION_TTL_SECONDS,
               httponly=True,      # 前端 JS 读不到,防 XSS 偷会话
               samesite="lax")     # 站内跳转带 cookie,第三方站点带不上
```

Cookie 是 `HttpOnly`，JS 根本读不到 → XSS 也偷不走登录态。反过来，token 存 `localStorage` 才是容易被 XSS 捞走的做法。**这块不用动。**

唯一建议补的是 `secure=True`（详见第 8 章 R5）。

至于我上一轮问的「公开性」——那是另一件事：站点公开后**登录页**外人能打开（只能看到密码框），数据全在闸门后面。这个可以接受。

---

## 1. 从代码里挖出来的硬约束

这几条决定了「怎么做」，照着通用教程抄一定会踩：

| # | 约束 | 代码依据 | 对部署的影响 |
|---|---|---|---|
| C1 | 数据库与上传原件都在 `<项目根>/resources/` 一棵树下 | `settings.py:16` `RESOURCES_DIR = PROJECT_ROOT / "resources"` | **必须挂 volume**，否则每次部署清零（库 + 照片 + 资料全没） |
| C2 | 会话是**进程内字典** `_SESSIONS`，不是 JWT，也不落库 | `tools/session.py`，注释写明"存内存不存库/重启掉登录" | **只能 `--workers 1`**，禁止多副本；重启=全员登出 |
| C3 | `RESOURCES_DIR` **不可用环境变量覆盖**（只有 `REPOS_DIR`、`CORS_ORIGINS` 可覆盖） | `settings.py:16 / :21 / :25` | volume 得挂到容器内 `/app/resources`，保证 `PROJECT_ROOT=/app` |
| C4 | **后端没有任何上传体积限制** | `file.py`/`photo.py` 里只有 `type: Form(max_length=20)` 这类字段约束 | 真闸门在 nginx，**默认 `client_max_body_size` 只有 1MB**，而前端提示"≤50MB" → 不配就 413 |
| C5 | 前端所有请求走**相对路径** `/api` | `api/http.ts:18` + `FilesView`/`PhotosView`/`PrivateView` 里的 inline `/api` 路径 | **同源反代是唯一"前端零改动"的走法**——正好匹配你的形态 |
| C6 | 「在线看代码」的 `pull`/`reindex` 会**写** `REPOS_DIR` | `settings.py:21` 默认 `F:/code/project` | 服务器上要指到 Linux 路径；且别让它和部署用的工作区是同一个（见 R3） |
| C7 | 路由是 `createWebHistory` | `router/index.ts:9` | nginx 必须配 SPA fallback（`try_files ... /index.html`），否则刷新子页面 404 |

---

## 2. 目标拓扑

```
浏览器
  │ 443 (HTTPS)
  ▼
[ 前置网关 Caddy 或 nginx ]        ← 只有一台需要对外暴露
  ├── /            ──▶ [ web 容器：nginx + dist ]        ← 前端
  └── /api         ──▶ [ api 容器：uvicorn ×1 进程 ]      ← 后端
                              ├── volume: resources/      (SQLite + 照片 + 资料)
                              └── ro 挂载: /srv/repos      (在线看代码只读读)
```

关键点：**前端和后端在同一个对外源下**，所以 `/api` 是相对路径、零 CORS、Cookie 同源自动带。

---

## 3. 服务器目录与挂载设计

```
/srv/yuepan/                        部署目录（compose 文件 + .env，只放配置不放数据）
  ├── docker-compose.yml
  ├── .env                          REPOS_DIR 等
  └── data/resources/     ←──────   volume 落地：库 + 照片 + 资料原件【必须备份】

/srv/repos/yuepan/                  「在线看代码」读的独立 clone（与部署目录分开）
```

**为什么 `data/` 与部署目录分开**：部署目录会被 CD 反复覆盖/重建，数据目录绝不能在那个里面。这是 C1 的直接推论。

---

## 4. 待建文件清单（规划，本轮不写）

| 文件 | 作用 | 要点 |
|---|---|---|
| `back-yueyue/Dockerfile` | 后端镜像 | `python:3.12-slim`；依赖用 `uv sync --frozen`（有 `uv.lock`）；启动 `uvicorn app.src.main:app --host 0.0.0.0 --port 8000 --workers 1`（**单进程，C2**）；工作目录 `/app`（**C3**） |
| `front-yueyue/Dockerfile` | 前端镜像 | 两阶段：`node:22-alpine` 构建 → `nginx:alpine` 托管 `dist` |
| `front-yueyue/nginx.conf` | 静态 + 反代 | SPA fallback（**C7**）、`client_max_body_size 60m`（**C4**）、`location /api` 反代、代理头、`/assets/` 长缓存而 `index.html` 不缓存 |
| `docker-compose.yml` | 编排 | `web` + `api` 两服务；named volume 挂 `/app/resources`；`/srv/repos` 只读挂载 + `REPOS_DIR=/srv/repos` |
| `.dockerignore` ×2 | 瘦身构建上下文 | 排除 `node_modules/`、`.venv/`、`dist/`、`resources/`（**别把本机数据库烤进镜像**） |
| `.github/workflows/ci.yml` | CI | 见第 5 章 |
| `.github/workflows/cd.yml` | CD | 见第 6 章 |

> 说明：Caddy 替代前置 nginx 更省事（一句域名自动 HTTPS）；若你已有 nginx，就在它里面加 `client_max_body_size` 和 `/api` 反代，前端容器里的 nginx 只管静态。

---

## 5. CI 设计

**触发**：`push` 到 `main` + 所有 `pull_request`。

三个 job（并行）：

| job | 步骤 | 说明 |
|---|---|---|
| `frontend` | `actions/setup-node@v4`(node 22, cache npm) → `npm ci` → `npm run build` | `build` 脚本是 `vue-tsc -b && vite build`，类型错误会直接失败 |
| `backend` | `actions/setup-python@v5`(3.12) + `astral-sh/setup-uv` → `uv run --with httpx python smoke_test.py` | 冒烟脚本用 `TestClient` 把 `RESOURCES_DIR` 沙箱到系统临时目录，**不碰真库真盘**（脚本头注释写明），CI 里跑很安全 |
| `docker` | `docker/build-push-action` **只构建不推送** | 防止 Dockerfile 悄悄坏掉 |

**待确认项（我没验证，别写死）**：`smoke_test.py` 期望输出 `43/43`，但要确认它在**失败时是否返回非零退出码**。若不返回，CI 里得加断言（如 `| tee` 后 `grep -q "43/43"`），否则测试红了你也不知道。

**可选加分**：给 CI 加 concurrency（同分支新 push 取消旧跑）、paths 过滤（只改文档就不跑）。

---

## 6. CD 设计：两条路线

### 路线 1（推荐）：构建镜像 → 推 GHCR → SSH 让服务器拉

```
CI 绿 → buildx 构建 web/api 两镜像 → 推 ghcr.io/<owner>/yuepan-{web,api}:<sha 与 latest>
      → Actions 用 SSH 连服务器执行: docker compose pull && docker compose up -d
```

- **需要配 Secrets**：`SSH_HOST`、`SSH_USER`、`SSH_KEY`、`SSH_PORT`
- 好处：服务器**只拉镜像**，不用装构建环境；回滚 = 把 compose 里的 tag 换成上一个 sha
- 注意：public 仓库的 GHCR 包**默认是 private**，要么在 Package 设置里放开，要么服务器 `docker login ghcr.io`

### 路线 2（最简单）：SSH 进服务器就地构建

```
CI 绿 → SSH → cd /srv/yuepan && git pull && docker compose up -d --build
```

- 好处：不需要镜像仓库，配的 Secret 一样少
- 代价：服务器要装 buildx；每次全量构建（首次数分钟、后续有缓存）；且服务器上那份 git 工作区会被「在线看代码」的 pull 干扰（见 R3）

**建议**：先上路线 2 把链路跑通（改动小、好排错），跑顺了再换路线 1。这是我唯一建议分两步的地方。

**部署方式**：`docker compose up -d` 是滚动替换，配合 volume 不会动数据；后端会重启 → **登录态掉一次**（C2 的必然结果，可接受）。

---

## 7. 首次上线 checklist

按顺序做，第 6 条最容易忘：

1. 服务器装 Docker + compose plugin
2. `git clone` 一份到 `/srv/repos/yuepan`（**给「在线看代码」用**，不是部署目录）
3. 建 `/srv/yuepan/data/resources/`（先空着，容器启动时 `init_db` 会自动建表）
4. 写 `/srv/yuepan/.env`：`REPOS_DIR=/srv/repos`（同源反代的话 `CORS_ORIGINS` 可不设）
5. `docker compose up -d`，访问一次确认起来了
6. ⚠️ **立刻用 `admin` / `123456` 登录，改主密码 + 改小屋解锁密码** —— 这是代码里写死的播种口令（`bootstrap.py` 建表时直插）
7. 配 HTTPS（Caddy 一行域名自动签发；nginx 则 certbot）
8. 确认 nginx `client_max_body_size 60m` 生效 —— **传一张 2MB 的照片验证**（C4）
9. 给 `/srv/yuepan/data/resources` 配定时备份（cron 打包到别处/异地）
10. 补 `secure=True`（见 R5）

---

## 8. 风险清单

| # | 风险 | 后果 | 对策 |
|---|---|---|---|
| R1 | `resources/` 没挂 volume | **每次部署数据全丢**（库+照片+资料） | compose 里显式 named volume / bind mount；上线前先空跑一次部署再验证数据还在 |
| R2 | 起了多 worker / 多副本 | 会话互相不认，登录态随机失效 | `--workers 1`；compose 里 `replicas: 1`；别挂到会扩缩容的编排上 |
| R3 | 「在线看代码」的 `pull` 改了服务器上的 git 工作区 | 若与部署目录同一份，会把部署内容改脏 | `/srv/repos/yuepan` 用**独立 clone**，与 `/srv/yuepan` 分开 |
| R4 | 上传 >1MB 直接 413 | 传照片/资料全失败 | nginx `client_max_body_size 60m`（C4） |
| R5 | Cookie 没有 `secure` 标志 | HTTPS 下仍可能被降级明文带出去 | `login.py:36` 加 `secure=True`（需先确保全站 HTTPS） |
| R6 | 仓库是 **public** | 密钥泄漏面 | Dockerfile / compose / nginx.conf 里**零密钥**；密钥走 GitHub Secrets + 服务器 `.env` |
| R7 | 内存会话在重启/部署时清空 | 每次部署都要重新登录 | 已知取舍，代码注释里也是这么选的；不必改 |
| R8 | SPA 刷新子页面 404 | `/notes/12` 刷新报 404 | nginx `try_files $uri $uri/ /index.html`（C7） |

---

## 9. 本轮不做什么

按你说的"**你只负责下规划**"，本轮：

- ❌ 不写任何 Dockerfile / nginx.conf / compose / workflow
- ❌ 不改任何现有代码（含 `login.py` 的 `secure=True`、`settings.py` 的 `RESOURCES_DIR` 环境变量化）
- ❌ 不碰服务器、不配 GitHub Secrets

等你确认规划、并告诉我走**路线 1 还是路线 2**，我再进入实现。
