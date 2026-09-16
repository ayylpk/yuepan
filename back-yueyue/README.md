# back-yueyue · 月畔小站后端

FastAPI + SQLAlchemy 2.0 async + SQLite(aiosqlite 驱动),uv 管理。
小站主业:放各种资料和文件 —— 照片、资料都有"上传落盘 / 删除销户"的磁盘联动。

## 启动

```bash
cd back-yueyue
uv sync                    # 装依赖(第一次)
uv run python runApp.py    # 开发模式,热重载
# 或跳过 runApp.py: uv run uvicorn app.src.main:app --port 8000 --reload
```

- 接口文档: http://127.0.0.1:8000/docs (Swagger,能直接点)
- 冒烟请求样例: `test_main.http`(IDEA 里点绿色箭头;photo/file 上传样例引用
  `smoke/sample.png`,那是测试用真图,别删)

## 目录约定(三层架构 + 磁盘资源区)

```
back-yueyue/
├── runApp.py                     # 入口:起 uvicorn(≈ main 方法)
├── test_main.http                # 接口冒烟样例
├── resources/                    # ★ 磁盘资源唯一真相源(运行时生成内容,别提交 git)
│   ├── database/yueyue.db        #   SQLite 整站单库
│   ├── photo/                    #   相册落盘:时间戳+4随机字符命名(storage.py 生成)
│   └── file/                     #   资料落盘:同规则
├── smoke/sample.png              # 上传冒烟用的真图
└── app/
    ├── common/                   # 公共件,不属于业务三层
    │   ├── result/               # 统一返回体:Result[T] / PageResult[T]
    │   ├── config/settings.py    # 全局路径(PROJECT_ROOT/RESOURCES_DIR)、API 前缀、会话参数
    │   └── schemas/<domain>/     # DTO,一类一文件(目录/文件名 snake_case,类 PascalCase)
    │       ├── diary/            #   diary_create / diary_update / diary_response ✅ 模板
    │       ├── photo/            #   photo_update / photo_response(上传走 multipart,无 create DTO)
    │       ├── file/             #   file_update / file_info_response(同上)
    │       └── user/ project/ tech/ code/
    ├── database/                 # 数据层三件套(9/16 从单体 db.py 拆开)
    │   ├── engine.py             #   连接/会话/get_db(≈ DataSource + @Transactional 边界)
    │   ├── models.py             #   全部实体(≈ @Entity 全家)
    │   └── bootstrap.py          #   建表 + 种子 admin(≈ ApplicationRunner + schema.sql)
    ├── tools/
    │   ├── storage.py            # ★ 统一磁盘落盘:save/delete/jail/命名/白黑名单/魔数
    │   ├── security.py           # pbkdf2 密码哈希/比对(≈ BCryptPasswordEncoder,标准库版)
    │   ├── session.py            # 服务端内存会话 + 依赖(sid 存 HttpOnly cookie,≈ HttpSession)
    │   └── code_indexer.py       # 代码索引 CLI/API 共用引擎(扫项目目录 → code_file_index 表)
    └── src/
        ├── main.py               # 应用装配:中间件、挂路由、启动钩子
        ├── api/                  # Controller 层:收参 → 调 service → 包返回体
        │   ├── diary.py photo.py file.py project.py tech.py code.py login.py user.py
        ├── service/              # 业务层:规则/校验/可见性/磁盘联动顺序都在这层
        └── repositories/         # DAO 层:只有 SQL,无业务
```

**命名纪律(9/16 起全站统一)**:目录和文件名 PEP8 snake_case,类名 PascalCase,
一个 DTO 一个文件。历史上 Code/Photo/Project/Tech 大写包、`photoCreate.py` 驼峰文件、
`Result/` 大写包已一次性改齐,别再长回去。

## 请求流程(以"上传照片"为例)

```
POST /api/photo  (multipart: file + type + role)
  → api/photo.py       解 multipart + 登录闸门(LoginUser)         (不判业务)
  → photo_service.create_photo   参数校验 → storage.save 落盘 → 插行(炸了补偿删盘)
  → repositories/photo_repository.insert   add/commit/refresh,返回 ORM 行
  → service 包 PhotoResponse 回 api → 前端(含 id,出图走 /api/photo/{id}/file)
```

## 文件落盘约定(需求正身,实现在 tools/storage.py)

| 口径 | 规则 |
|---|---|
| 磁盘位置 | `resources/<分类>/`(photo=图片白名单,pdf/zip…=资料黑名单挡可执行) |
| 命名 | `时间戳_4位随机字符.扩展名`,如 `20260916213045_k7fp.jpg`(去易混字符 i l o 0 1) |
| 入库 path | **相对 resources/ 的正斜杠路径**(`"photo/….jpg"`),绝对路径永远不出 storage.py |
| 类型防线 | photo 白名单 + 文件头魔数复核(假 .jpg 直接 400);file 挡 exe/bat/ps1… 可执行 |
| 大小上限 | photo 20MB / file 50MB,分块写入,超限 413 且半成品当场清掉 |
| 读写闸门 | 进出一律过 `jail()`(拒 `..`/绝对路径/盘符/软链跳出;代码浏览器同源共用) |
| 顺序纪律 | **先落盘再插行**(插失败补偿删盘);**先删行再删盘**(指针不先于实物消失) |
| 对外访问 | 不挂 StaticFiles,一律 API:`GET /api/photo/{id}/file`、`GET /api/file/{id}/download`,role 闸门在服务里 |

## role 约定

| role | 含义 | 规则 |
|---|---|---|
| 0 | 正常/公开 | 所有人可见 |
| 1 | 隐私(小屋) | 未解锁会话**完全不可见**:列表里不出现,单查/出图/下载按 404 回(不用 403,防状态码探测) |

- 修改接口支持只传 `{"role": 0}` 或 `{"role": 1}` 单改这一字段(上锁/摆回)。
- **page 也吃闸门**(9/16 补):未解锁时 `?role=1` 一律强制回公开,diary/photo/file 同治。
- diary 的 get/put/delete 原来靠 `?show_private=true` 查询参数放行 —— 那是可以被人
  随手拼 URL 绕过的假闸门,已换成 `ShowPrivate` 会话依赖(解锁态真源只在服务端 session)。

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
  | POST /private/unlock | password | 对 → 会话 private=True(role=1 可见) |
  | POST /private/lock | — | 手动落锁 |
  | POST /private/password | old_password,new_password | 换小屋锁芯 |
- `/api/user/` GET/PUT:查/改资料,需登录;PUT 走 PATCH 语义,**password 不在白名单**
  (防"知道 id 就能顶号",改密只认 /api/auth/password 那条验旧密码的路)。

## 相册/资料 API(9/16 落地)

| 端点 | 登录 | 说明 |
|---|---|---|
| GET /api/photo/page?page&page_size&role | — | 分页;未解锁时 role 强制 0 |
| GET /api/photo/{id} | — | 单条 VO(不回传磁盘 path) |
| GET /api/photo/{id}/file | — | 出图 FileResponse,role 闸门内置 |
| POST /api/photo | ✅ | multipart:file/type/role,落盘+插行 |
| PUT /api/photo/{id} | ✅ | 只可改 type/role |
| DELETE /api/photo/{id} | ✅ | **删行 + 删磁盘文件** |
| GET /api/file/page 等五件 | 同上 | 前缀换 /api/file;/{id}/download 为 attachment 带原名 |

## 9/16 结构大整理·迁移记录

一次性改名/搬位,已在开发机执行(新库直接按新结构长,无需迁移):

1. 全目录/文件 snake_case 统一(schemas 包名、DTO 文件名、`Result/`→`result/`、
   `config/config.py`→`settings.py`);DTO 类名 `PhotoCreateSchema/photoUpdate` 等歧名改齐
   `PhotoCreate/PhotoUpdate` 风格(相册/资料上传改走 multipart,create DTO 删除)。
2. `app/database/db.py` 一拆三(engine/models/bootstrap),`tools/db.py` 并入 bootstrap;
3. 真库 `app/database/resources/database/yueyue.db` → **`resources/database/yueyue.db`**;
4. 表结构:旧空表 `photos` DROP 重建(补 name/size/updated_at 列);
   代码索引表 **`files` → `code_file_index`**(实体 `Files` → `CodeFileIndex`),
   索引数据可整项目重建,迁移 = drop + `uv run python -m app.tools.code_indexer --all`;
5. 新表 `file`(资料库)上线;`resources/Files→file`、空壳 `resources/Project` 删除;
6. `python-multipart` 进依赖(multipart 上传解析必需)。

## 待接入(TODO,写这备忘)

1. ~~`/api/projects`、`/api/code/*`~~ ✅ 早已完成
2. ~~相册/资料落盘存储(本次)~~ ✅ 9/16 完成(上两节)
3. `/api/videos`:上传 + Range 206 流播(前端 VideosView 已按契约画好页);
   地基就是 `tools/storage.py`(save/delete/jail 现成),缺 Video 表 + 三件套 + Range 应答
4. 上传侧:图片缩略图、exif 清理等,等到前端打磨期再议
