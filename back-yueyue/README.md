# back-yueyue · 月畔小站后端

FastAPI + SQLite(标准库自带,零额外依赖),uv 管理。

## 启动

```bash
cd back-yueyue
uv sync                    # 装依赖(第一次)
uv run python runApp.py    # 开发模式,热重载
# 或跳过 runApp.py: uv run uvicorn app.src.main:app --port 8000 --reload
```

- 接口文档: http://127.0.0.1:8000/docs (Swagger,能直接点)
- 冒烟请求样例: `test_main.http`(IDEA 里点绿色箭头)

## 目录约定(三层架构)

```
back-yueyue/
├── runApp.py                     # 入口:起 uvicorn(≈ main 方法)
├── test_main.http                # 接口冒烟样例
├── app/
│   ├── common/                   # 公共件,不属于业务三层
│   │   ├── Result/               # 统一返回体:Result[T] / PageResult[T]
│   │   ├── config/config.py      # 全局路径、API 前缀、会话参数
│   │   └── schemas/<domain>/     # DTO,一类一文件(PascalCase 文件名)
│   │       ├── diary/            #   DiaryCreate / DiaryUpdate / DiaryResponse ✅ 模板
│   │       └── user/             #   UserCreate / UserUpdate / UserResponse
│   │                             #   + LoginRequest / PasswordUpdate / UsernameUpdate / PrivateUnlock
│   ├── database/                 # SQLite 数据文件(diary.db + user.db,运行时生成,别提交 git)
│   ├── tools/
│   │   ├── db.py                 # 连接 + 建表 + 种子(≈ DataSource + schema.sql)✅ 模板
│   │   ├── security.py           # pbkdf2 密码哈希/比对(≈ BCryptPasswordEncoder,标准库版)
│   │   └── session.py            # 服务端内存会话 + 依赖(sid 存 HttpOnly cookie,≈ HttpSession)
│   └── src/
│       ├── main.py               # 应用装配:中间件、挂路由、启动钩子
│       ├── api/                  # Controller 层:收参 → 调 service → 包 Result
│       │   ├── login.py          #   /api/auth/* 八端点:登录/登出/me/改密/改名/小屋锁 ✅
│       │   ├── user.py           #   /api/user/ 查/改资料(需登录) ✅
│       │   └── diary.py          #   ✅ 模板(可见性已接 session)
│       ├── service/              # 业务层:规则/校验/可见性都在这层
│       │   ├── diary_service.py  #   ✅ 模板
│       │   └── user_service.py   #   ✅
│       └── repositories/         # DAO 层:只有 SQL,? 占位符,无业务
│           ├── diary_repository.py # ✅ 模板
│           └── user_repository.py  # ✅
```

## 请求流程(以"修改日记"为例)

```
PUT /api/diary/3  {"role": 1}
  → api/diary.py      解参 + 依赖注入连接        (不判业务)
  → service/diary_service.update_diary  可见性 404 判定 + 字段白名单 + exclude_unset
  → repositories/diary_repository.update_fields  拼 SET,? 占位执行 UPDATE
  → service 拿回新行 → api 包 Result[DiaryResponse].success → 前端
```

## role 约定

| role | 含义 | 规则 |
|---|---|---|
| 0 | 正常/公开 | 所有人可见 |
| 1 | 隐私(小屋) | 未解锁会话**完全不可见**:列表里不出现,单查按 404 回(不用 403,防状态码探测) |

- 建表层 CHECK(role IN (0,1)) 兜底;DTO 层 ge/le 校验;两头都锁死。
- 修改接口支持只传 `{"role": 0}` 或 `{"role": 1}` 单改这一字段(上锁/摆回)。

## 登录/会话(9/16 落地)

- 方案:**服务端内存会话,不用 JWT**。登录成功 → `tools/session.py` 生成随机 sid →
  `Set-Cookie: yueyue_sid=...`(HttpOnly + samesite=lax,7 天);状态真源在服务器字典里,
  退出/到期即删。代价:uvicorn 重启会掉登录(重登即可,数据不丢)。
- 默认账号 `admin / 123456`,小屋私钥 `123456`(user 表空时种子直插,密码入库前先 pbkdf2 哈希)。
- `/api/auth/*` 契约(前端 `stores/auth.ts` 已固化):
  | 端点 | 入参 | 说明 |
  |---|---|---|
  | POST /login | username,password | 对 → Set-Cookie;错 → 401(话术不区分哪个错) |
  | POST /logout | — | 删会话 + 抹 cookie |
  | GET /me | — | **不 401**:回 `{logged_in, username?, private?}`,路由闸门用 |
  | POST /password | old_password,new_password | 先验旧 |
  | POST /username | new_username,password | 先验当前密码;改名后会话显示名同步 |
  | POST /private/unlock | password | 对 → 会话 private=True(日记 role=1 可见) |
  | POST /private/lock | — | 手动落锁 |
  | POST /private/password | old_password,new_password | 换小屋锁芯 |
- `/api/user/` GET/PUT:查/改资料,需登录;PUT 走 PATCH 语义,**password 不在白名单**
  (防"知道 id 就能顶号",改密只认 /api/auth/password 那条验旧密码的路)。
- 日记可见性接线:`api/diary.py` 用 `ShowPrivate` 依赖(读会话标记),未解锁时 role=1 一律 404。

## 待接入(TODO,写这备忘)

1. ~~`api/login.py` + `schemas/user/`:session 登录~~ ✅ 9/16 完成(上表)
2. ~~diary `SHOW_PRIVATE=False` 换成读会话~~ ✅ 同上,一起接的
3. ~~前端 `/api/notes` 口径统一成日记+role~~ ✅ 前端整站已是 `/api/diary`
4. 剩余接口(前端已按契约画好页):`/api/videos`(+upload/stream Range 206)、`/api/projects`、`/api/code/*`(白名单读 git)
