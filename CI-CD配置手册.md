# 月畔小站 · GitHub CI/CD 配置手册

> 面向第一次配 CI/CD。每一步都写了**点哪里**、**为什么**、**错了会怎样**。
> 仓库：`https://github.com/ayylpk/yuepan`

---

## 0. 先建立心智模型

一次 `git push` 之后发生的事（对应上面那张流程图）：

```
① 你 push 到 main
② GitHub 自动跑 CI：前端构建 / 后端冒烟 / 镜像试构建（三个 job 并行，互不依赖）
③ CI 全绿 → 触发 CD（CI 红了或取消，CD 什么都不做）
④ CD 用 SSH 进服务器，把代码对齐到"CI 跑的那个 commit"
⑤ 服务器 docker compose 重建容器，新版本上线
```

**关键点**：② 不需要任何配置，④ 需要 4 个 Secret，⑤ 需要服务器先具备前置条件。
所以正确的上手顺序是 **先把 ② 跑通，再配 ④⑤**。

---

## 1. 第一步:只上 CI,先不碰 CD

先确认仓库允许跑 Actions：打开
`https://github.com/ayylpk/yuepan/settings/actions`
→ **Actions permissions** 选 `Allow all actions and reusable workflows`（个人仓库默认就是它）。

然后**只提交 `ci.yml`，先别提交 `cd.yml`**：

```bash
git add .github/workflows/ci.yml
git commit -m "CI: 前端构建 + 后端冒烟 + 镜像试构建"
git push
```

> 为什么先不放 cd.yml：Secret 还没配，CD 一定会红。先看到 CI 绿，再上 CD，心理负担小、排错面窄。

push 完打开 `https://github.com/ayylpk/yuepan/actions`，你应该看到三个 job：

| job | 干什么 | 大概耗时 |
|---|---|---|
| 前端构建(含类型检查) | `npm ci` + `npm run build`（`vue-tsc` 类型错误会让它红） | 1–2 分钟 |
| 后端冒烟(43 项) | `uv run --with httpx2 python smoke_test.py` | 30 秒左右 |
| 镜像可构建 | 真的构建两个 Docker 镜像（不推送），确认 Dockerfile 没坏 | 2–5 分钟（首次慢） |

**三个都打勾绿了**再往下走。红的话：点进 job → 展开出错的 step 看日志，日志里会直接给出错行。

---

## 2. 第二步:造一把"部署专用"的 SSH 密钥

**在你自己电脑上跑**（不是服务器）。核心原则：给 CD 一把**单独的钥匙**，不要用你平时登录的那把私钥。

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/yuepan_deploy -N ""
```

会生成两个文件：

| 文件 | 是什么 | 去哪 |
|---|---|---|
| `~/.ssh/yuepan_deploy` | **私钥** | 贴进 GitHub Secret。**永远不要提交、不要发给任何人** |
| `~/.ssh/yuepan_deploy.pub` | 公钥 | 装到服务器的 `authorized_keys` |

---

## 3. 第三步:把公钥装到服务器

```bash
ssh-copy-id -i ~/.ssh/yuepan_deploy.pub 你的用户@你的服务器
```

`ssh-copy-id` 不存在（Windows 常见）就手动来：

```bash
cat ~/.ssh/yuepan_deploy.pub | ssh 你的用户@你的服务器 \
  "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
```

验证一下这把钥匙能单独登录（**这一步必须成功，否则后面 CD 一定失败**）：

```bash
ssh -i ~/.ssh/yuepan_deploy 你的用户@你的服务器 "echo 登录成功 && docker compose version"
```

---

## 4. 第四步:在 GitHub 填 4 个 Secret + 1 个 Variable

打开 `https://github.com/ayylpk/yuepan/settings/secrets/actions`

### 4.1 Secrets 标签页 → `New repository secret`，一个一个建

| Secret 名 | 值 | 说明 |
|---|---|---|
| `SSH_HOST` | 服务器 IP 或域名 | 例如 `1.2.3.4` 或 `yuepan.example.com` |
| `SSH_USER` | 登录用户名 | **本仓库这台是 `ubuntu`**（不是 root）；例如 `root` / `deploy` |
| `SSH_KEY` | 私钥**全文** | 用 `cat ~/.ssh/yuepan_deploy` 打印后**整段**复制，必须包含 `-----BEGIN ...-----` 和 `-----END ...-----` 两行 |
| `SSH_PORT` | 例如 `22` | 可留空（工作流里默认回落 22） |

> **这 4 个名字不是必须的**：`cd.yml` 里做了一张别名表，下面这些名字同样认（大小写不敏感），
> 还同时兼容 `vars.*`（万一建到了 Variables 标签页也能跑）：
> - 地址：`YUEPANIP` / `SSH_HOST` / `SERVER_HOST` / `HOST` / `IP` / `SERVER_IP` / `ADDRESS` / `DOMAIN`
> - 用户：`SSH_USER` / `SERVER_USER` / `USER` / `USERNAME` / `NAME` / `LOGIN`
> - 私钥：`SSH_KEY` / `SSH_PRIVATE_KEY` / `KEY` / `PRIVATE_KEY` / `SERVER_KEY`
>
> **名字必须建在 `Secrets` 标签页**（Repository secrets）；建到 `Variables` 虽也能被上面兜底，但那是明文存储，私钥别这么干。
> 另外 Secrets 页有 `Repository secrets` 和 `Environment secrets` 两类，**环境级密钥必须在 job 里声明 `environment:` 才生效**，请建成仓库级。
>
> 名字到底配对没有，不用猜：CD 每次跑的第一步就是打印一张命中表
> （`YUEPANIP=已配 SSH_HOST=未配 …`），缺哪个还会逐条点名。

### 4.2 Variables 标签页 → `New repository variable`

切到 `https://github.com/ayylpk/yuepan/settings/variables/actions`

| Variable 名 | 值 | 说明 |
|---|---|---|
| `DEPLOY_DIR` | 服务器上的部署目录 | 例如 `/srv/yuepan`；不填则默认用 `/srv/yuepan` |

> **Secret 和 Variable 的区别**：Secret 加密存储、日志里自动打码、建完不能再读回；Variable 是明文，用于非敏感配置。
> 私钥放 Secret 是安全的——`fork` 出去的仓库拿不到，PR 也不会拿到（而且我们的 CD 只跑在 main 上）。

---

## 5. 第五步:服务器前置条件

CD 的工作流假设服务器上这些已经就绪，缺一条就会报错：

```bash
# 1) Docker + compose plugin（注意 compose 是插件，不是老的 docker-compose）
docker --version && docker compose version

# 2) 当前用户在 docker 组里，否则每次都得 sudo（而 CD 里没写 sudo）
sudo usermod -aG docker $USER   # 执行后要重新登录一次才生效
docker ps                       # 不加 sudo 能跑通才算好

# 3) 部署目录是一个 git clone
sudo git clone https://github.com/ayylpk/yuepan.git /srv/yuepan
cd /srv/yuepan && git log --oneline -1

# 4) 配好 .env（CD 不会替你建）
cd /srv/yuepan && cp .env.example .env && vi .env

# 5) 「在线看代码」用的独立 clone（不要指到部署目录本身）
sudo git clone https://github.com/ayylpk/yuepan.git /srv/repos/yuepan
# 并把 .env 里的 REPOS_HOST_DIR 指向 /srv/repos
```

> **2026-10-09 实测记录（`101.42.105.26`，Ubuntu 22.04.5 / 2 核 / 1.9GB 内存）**
>
> 这台机上前置条件**已全部配好**，配置过程中踩到的坑列在这（换机器时照抄）：
>
> | 事项 | 实际情况 / 做法 |
> |---|---|
> | **登录用户** | 是 **`ubuntu`**，不是 `root`（`root` 用本机两把钥匙都被拒）。CD 的 `NAME` 必须填 `ubuntu` |
> | **内存偏小** | 1.9GB / 2 核，构建前端镜像有 OOM 风险 → 加了 **2GB swap** 并写进 `/etc/fstab` |
> | **docker 组** | ubuntu 已在 docker 组，`docker ps` 不用 sudo |
> | **宿主 80 端口** | 空的，宿主没装 nginx/caddy → 直接把容器映射到 80 |
> | **云安全组** | **放行 80、屏蔽 8080**（80 探测是"拒绝=RST"说明云侧通；8080 是"超时=丢包"说明云侧挡）。用高位端口要先去控制台放行，否则外网连不上而 nginx 日志里毫无记录 |
> | **`/srv` 是 root 的** | `git clone` 到 `/srv` 会 `Permission denied`。先 `sudo mkdir -p /srv/yuepan && sudo chown ubuntu:ubuntu /srv/yuepan`，再以 ubuntu 身份 clone；改完属主立刻 `git config --global --add safe.directory /srv/yuepan`，否则 `dubious ownership` 会让 `set -e` 中断整段脚本 |
> | **首次 clone 很慢** | 服务器直连 GitHub 只有 **~48KB/s**（23MB 要十几分钟）。改从本机 `git bundle create … --all` + `scp`（本机到服务器 **3MB/s**，23MB 用 8 秒）再 `git clone <bundle>` + `git remote set-url origin <GitHub> URL`。同一份 bundle 可 clone 出部署目录和 repos 目录两份 |
> | **apt 源** | `deb.debian.org` 实测 **48KB/s**，装 git 那步会卡很久 → `.env` 设 `DEBIAN_MIRROR=mirrors.tencentyun.com`（**19.3MB/s**） |
> | **Docker 镜像源** | `registry-1.docker.io` 在服务器上**完全不可达（000）** → `daemon.json` 配 `mirror.ccs.tencentyun.com`。注意：镜像加速只覆盖 docker.io，**管不到 `ghcr.io`**（`ghcr.io/astral-sh/uv` 那层实测 40KB/s，22MB 拉了 8 分钟，但只需一次，之后进本地缓存） |
> | **pip / npm 源** | `pypi.org` 约 10s、`registry.npmjs.org` 0.8s，都不用改 |

---

## 6. 第六步:上 CD 并首次触发

```bash
git add .github/workflows/cd.yml
git commit -m "CD: CI 通过后 SSH 部署到服务器"
git push
```

这个 push 会先跑 CI；CI 绿了之后 CD 自动接上。观察地址：
`https://github.com/ayylpk/yuepan/actions`

想手动再发一次（比如你改了服务器上的 `.env`）：进 **CD** 这个 workflow → 右上角 **Run workflow**。

---

## 7. 怎么确认部署真的成功了

> **2026-10-09 已实跑通过**（服务器 `101.42.105.26`，commit `996ba7d`）。
> 下表是从**公网**发起的实测结果，不是"应该能行"：

| 验的项 | 命令 | 结果 |
|---|---|---|
| 首页 | `curl -o /dev/null -w '%{http_code}' http://101.42.105.26/` | **200**（0.07s） |
| SPA 回落（history 模式） | `curl … http://101.42.105.26/notes/1` | **200**，返回的是 `index.html` |
| 反代 + 前缀没被剥 | `curl http://101.42.105.26/api/health` | `{"code":200,…,"service":"yueyue-back"}` |
| **上传不被 413 挡** | 登录后 `POST /api/file` 传 **2MB** 文件 | **200**（默认 1MB 早就 413 了）→ `client_max_body_size 60m` 生效 |
| 数据落在宿主机 | `ls /srv/yuepan/data/resources/` | 有 `database/`、`file/` 两个目录（volume 挂载正确，部署不会清零） |
| index.html 不缓存 | `curl -I http://…/index.html` | `Cache-Control: no-cache`（发版后不会卡在旧壳） |

（测上传后会留下测试文件，记得删掉：`curl -b ck -X DELETE http://…/api/file/<id>`。）

平时自己复查（在服务器上）：

```bash
cd /srv/yuepan
docker compose ps                  # 两个服务都应是 Up / healthy
docker compose logs -f api --tail 50
curl -s localhost/api/health       # 期望 {"code":200,...}
curl -sI localhost/ | head -1      # 期望 200
```

---

## 8. 日常怎么用

| 想做的事 | 怎么做 |
|---|---|
| 发新版本 | 改代码 → `git push` 到 main。剩下全自动 |
| 看部署历史 | `https://github.com/ayylpk/yuepan/actions` |
| 重跑失败的那次 | 进那次 run → 右上 **Re-run failed jobs** |
| 看更详细的日志 | 在仓库 Secret 里加一个 `ACTIONS_STEP_DEBUG` = `true`，再重跑 |
| **回滚** | 工作流不支持回滚，去服务器手动做（见下） |

回滚（改坏了，退回上一个版本）：

```bash
cd /srv/yuepan
git log --oneline -5            # 找到要退到的 sha
git reset --hard <旧sha>
docker compose up -d --build
```

> 回滚**不会**动 `data/resources/`（你的库和照片），因为它不在 git 里。

---

## 9. 常见坑:对号入座

| 症状 | 原因 | 怎么办 |
|---|---|---|
| **CD 完全不触发** | ① `cd.yml` 里写的是 `workflows: ["CI"]`，必须与 `ci.yml` 顶部的 `name: CI` **完全一致**（大小写、空格都算）；② CI 从没在 main 上成功跑过一次 | 核对两个文件的 name；确认 Actions 里 CI 是绿的 |
| CD 报 `error: missing server host`（几秒就挂，`Run entrypoint.sh` 里出现） | **Secret 名字对不上**，`secrets.SSH_HOST` 取到了空值。常见两种情况：① 建的时候用了别的名字（如 `SERVER_HOST`）；② 建在了 Variables 标签页或 Environment secrets 里 | 看 CD 第一步打印的命中表；工作流已兼容 `SERVER_HOST`/`SERVER_USER`/`SSH_PRIVATE_KEY` 三个别名，其余名字请改名或改 `cd.yml` 的 `env:` 那几行 |
| CD 日志顶部有 `Unexpected input(s) 'script_stop'` | `appleboy/ssh-action@v1` 移除了 `script_stop` 参数（改用脚本文本里的 `set -e`），传了没副作用但会有警告 | 已从 `cd.yml` 撤掉；自己改的时候也别再加回来 |
| **部署成功但外网打不开，且 nginx 日志里没有任何请求记录** | 云安全组没放行该端口（用 8080 这类高位端口最常见） | 去控制台放行，或把 `.env` 的 `WEB_PORT` 改成 80。**判定方法**：从外部 `python -c "socket.create_connection((ip,port))"` —— 报「超时」=被丢包(云侧挡)，报「拒绝」=端口通但没监听(云侧放行) |
| **首次构建卡在装 git，日志十几分钟不动** | 基础镜像里的 apt 源是 `deb.debian.org`，国内实测仅 ~48KB/s | `.env` 设 `DEBIAN_MIRROR=mirrors.tencentyun.com`（或 aliyun），快约 400 倍。**别写死进 Dockerfile**——CI 跑在 GitHub 机器上，内网域名解析不了 |
| **`docker pull` 极慢或 000 不可达** | 国内服务器连 `registry-1.docker.io` 常被墙 | 配 `daemon.json` 的 `registry-mirrors`。但它**只管 docker.io，管不到 `ghcr.io`**；镜像里若引用了 ghcr 的基础镜像（如 `astral-sh/uv`），那层只能慢拉一次（之后进本地缓存） |
| **远程 SSH 命令超过 ~2 分钟就"无输出 + 退出码 1"，但命令其实执行了** | 长会话被掐断 | 远程耗时操作一律 `nohup … > /tmp/x.log 2>&1 &` 再轮询日志；别把长命令和 `set -e` 混在一起，否则会留下半成品（曾只 clone 出一个空仓库） |
| **CD 被触发、SSH 也通了，但部署的还是旧代码** | `concurrency: cancel-in-progress: false` 让部署排队，新提交那次会等旧的跑完 | 想立刻用新版：去 Actions 页面 **Cancel** 正在跑的那次（或在服务器上掐掉它的构建进程），已在跑的那次会记为失败 |
| CD 报 `Permission denied (publickey)` | 公钥没装对 / 私钥粘贴不完整 | 重跑第 3 步的验证命令 |
| CD 报 `docker: command not found` 或 `unknown command: compose` | 服务器只装了 docker，没装 compose 插件 | 装 `docker-compose-plugin` |
| CD 报 `permission denied ... docker.sock` | 用户不在 docker 组 | `usermod -aG docker` 后重新登录 |
| CD 报 `fatal: not a git repository` | `DEPLOY_DIR` 指错了，或那目录不是 clone 出来的 | 核对 Variable 与第 5 步 |
| 部署成功但页面还是旧的 | 浏览器缓存了 `index.html` | 硬刷新；`nginx.conf` 里已给 `index.html` 设了 `no-cache` |
| 服务器磁盘越来越满 | 每次重建都留旧镜像 | 工作流里已带 `docker image prune -f`；也可手动 `docker system prune` |
| 每次部署都要重新登录 | 会话在进程内存里，容器重启即清空 | **设计如此**（见 `tools/session.py` 的注释），不用修 |

---

## 10. 可选加固(不急,但值得)

1. **分支保护**：`Settings → Branches → Add branch ruleset`，对 `main` 勾选 *Require status checks to pass*，把 CI 三个 job 选上 → 以后就不能把没跑过 CI 的代码直接推进 main。
2. **部署密钥降权**（服务器上把 `~/.ssh/authorized_keys` 里那把公钥前面加限制）：
   ```
   command="cd /srv/yuepan && git fetch --all && git reset --hard origin/main && docker compose up -d --build",no-port-forwarding,no-pty,no-agent-forwarding ssh-ed25519 AAAA...
   ```
   这样这把钥匙**只能执行这一条命令**，泄漏了也干不了别的。
3. **README 状态徽章**：
   ```markdown
   ![CI](https://github.com/ayylpk/yuepan/actions/workflows/ci.yml/badge.svg)
   ```
4. **部署失败通知**：GitHub 默认会给你注册邮箱发失败邮件；够用。

---

## 11. 还没做的（按你说的放最后）

这两个属于"打包与 nginx"，等 GitHub 侧配完了再做：

- **两个镜像的实际构建验证**：本机 Docker Desktop 引擎当前**没起来**（`docker desktop start` 需要你手动启动应用）。你启动它之后我就跑 `docker compose build` + `docker compose up -d`，实测：首页能开、`/api/health` 通、SPA 子路由刷新不 404、**传一张 2MB 的图不被 413 挡**。
- **nginx.conf 的实际生效验证**：SPA 回落、`client_max_body_size`、反代与 Cookie 透传，都靠上面那次运行一起验。

在此之前，`Dockerfile` ×2、`nginx.conf`、`docker-compose.yml` 都只是**写好了但没跑过**——YAML 语法与 `docker compose config` 已校验通过，实际构建结果待验。
