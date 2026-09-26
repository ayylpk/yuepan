"""部署前冒烟(常备回归脚本)。跑法(在 back-yueyue/ 下):

    uv run --with httpx python smoke_test.py   # 期望输出 39/39

隔离手法:engine.py/storage.py 都是"自己 import 时"才从 settings 读 RESOURCES_DIR,
所以在 import app 之前把 settings.RESOURCES_DIR 指到系统临时目录沙箱,
全套真实代码(建表/播种/落盘/闸门)跑在沙箱里,真库真盘零接触。

写这套时踩过的口径坑(留字备忘,改脚本别退回去):
- TestClient cookie jar 会自动带登录态,"匿名"用例必须先显式 logout;
- /me 返回 Result 包 data,不是裸 dict;
- 登出再登录=新会话,小屋解锁标记清零,删 role=1 条目前要重新 unlock。
"""
import base64
import shutil
import sys
import tempfile
from pathlib import Path

TMP = Path(tempfile.gettempdir()) / "yueyue-smoke"
shutil.rmtree(TMP, ignore_errors=True)
(TMP / "resources").mkdir(parents=True)

import app.common.config.settings as settings  # noqa: E402

settings.RESOURCES_DIR = TMP / "resources"  # 必须在 import app.* 之前改

from fastapi.testclient import TestClient  # noqa: E402

from app.src.main import app  # noqa: E402

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

n = ok = 0


def check(label, cond):
    global n, ok
    n += 1
    if cond:
        ok += 1
        print(f"  PASS {label}")
    else:
        print(f"  FAIL {label}")


with TestClient(app) as c:  # lifespan → 沙箱建表 + seed admin/123456
    def login():
        r = c.post("/api/auth/login", json={"username": "admin", "password": "123456"})
        assert r.status_code == 200
        return c

    def anon():
        c.post("/api/auth/logout")
        return c

    print("== A 认证 ==")
    r = c.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    check("错密码拒登录", r.status_code >= 400)
    r = c.post("/api/auth/login", json={"username": "admin", "password": "123456"})
    check("对密码 200", r.status_code == 200)
    check("种下 yueyue_sid", "yueyue_sid" in dict(c.cookies))
    r = c.get("/api/auth/me")
    check("/me Result 包 data 返回 admin", r.json()["data"]["username"] == "admin")
    r = anon().get("/api/auth/me")
    check("登出后 /me 不抛 401 而是 logged_in=False",
          r.status_code == 200 and r.json()["data"]["logged_in"] is False)

    print("== B 日记(今日新闸门) ==")
    r = anon().post("/api/diary", json={"title": "匿名投毒", "role": 0})
    check("匿名 POST → 401(今天焊的闸门)", r.status_code == 401)
    login()
    pub = c.post("/api/diary", json={"title": "公开冒烟", "content": "x", "role": 0}).json()
    pri = c.post("/api/diary", json={"title": "隐私冒烟", "content": "s", "role": 1}).json()
    check("登录后可写(公开+隐私各一)", pub.get("id") and pri.get("id"))
    r = anon().get("/api/diary/page?page=1&page_size=50")
    ids = [d["id"] for d in r.json()["data"]]
    check("匿名可读列表且只见公开条", r.status_code == 200 and pub["id"] in ids and pri["id"] not in ids)
    r = anon().put(f"/api/diary/{pub['id']}", json={"title": "匿名改公开"})
    check("匿名 PUT 公开条 → 401(第二洞已焊)", r.status_code == 401)
    r = anon().delete(f"/api/diary/{pub['id']}")
    check("匿名 DELETE 公开条 → 401(第二洞已焊)", r.status_code == 401)
    login()
    check("未解锁读隐私条 → 404(非403)", c.get(f"/api/diary/{pri['id']}").status_code == 404)
    check("小屋错密码拒解锁", c.post("/api/auth/private/unlock", json={"password": "bad"}).status_code >= 400)
    check("小屋对密码解锁", c.post("/api/auth/private/unlock", json={"password": "123456"}).status_code == 200)
    check("解锁后隐私条可读", c.get(f"/api/diary/{pri['id']}").status_code == 200)
    ids = [d["id"] for d in c.get("/api/diary/page?page=1&page_size=50&role=1").json()["data"]]
    check("解锁后 role=1 列表含隐私条", pri["id"] in ids)
    r = c.put(f"/api/diary/{pub['id']}", json={"title": "登录改题"})
    check("登录 PUT 正常", r.status_code == 200 and r.json()["title"] == "登录改题")
    check("清场删两条", c.delete(f"/api/diary/{pub['id']}").status_code == 200
          and c.delete(f"/api/diary/{pri['id']}").status_code == 200)

    print("== C 照片 ==")
    login()
    r = c.post("/api/photo", files={"file": ("t.png", PNG, "image/png")}, data={"type": "smoke", "role": 0})
    check("真 PNG 上传 200", r.status_code == 200)
    pid = r.json()["id"]
    r = c.get(f"/api/photo/{pid}/file")
    check("回读字节一致", r.status_code == 200 and r.content == PNG)
    r = c.post("/api/photo", files={"file": ("fake.png", b"HELLO NOT PNG", "image/png")})
    check("假魔数 .png 拒收(4xx)", r.status_code >= 400)
    check("匿名传照片 → 401", anon().post("/api/photo", files={"file": ("t.png", PNG, "image/png")}).status_code == 401)
    login()
    check("删照片", c.delete(f"/api/photo/{pid}").status_code == 200)
    check("盘上文件跟删", not any((settings.RESOURCES_DIR / "photo").rglob("*.png")))

    print("== D 资料 ==")
    body = "冒烟文本内容 hello".encode()
    r = c.post("/api/file", files={"file": ("smoke 报告.txt", body, "text/plain")}, data={"role": 0})
    check("txt 原名上传 200", r.status_code == 200)
    fid = r.json()["id"]
    check("回显原文件名", "smoke" in r.json()["name"])
    r = c.get(f"/api/file/{fid}/raw")
    check("txt inline 直读", r.status_code == 200 and r.content == body)
    r = c.post("/api/file", files={"file": ("evil.html", b"<script>alert(1)</script>", "text/html")}, data={"role": 0})
    hid = r.json()["id"] if r.status_code == 200 else None
    check("html 能入库(黑名单不含它)", hid is not None)
    check("但 raw 拒 inline(防存储型XSS)", c.get(f"/api/file/{hid}/raw").status_code >= 400)
    r = c.post("/api/file", files={"file": ("x.exe", b"MZ..", "application/octet-stream")}, data={"role": 0})
    check("exe 黑名单拒收", r.status_code >= 400)
    sid_ = c.post("/api/file", files={"file": ("secret.txt", b"pv", "text/plain")}, data={"role": 1}).json()["id"]
    check("登出后(新会话=锁回)私有资料 404", anon().get(f"/api/file/{sid_}").status_code == 404)
    check("登出后公开资料仍可读", c.get(f"/api/file/{fid}").status_code == 200)
    login()
    c.post("/api/auth/private/unlock", json={"password": "123456"})  # 新会话要重新解锁才能删私有条
    r = c.put(f"/api/file/{fid}", json={"name": "改名后.txt"})
    check("改名 200", r.status_code == 200)
    r = c.get(f"/api/file/{fid}/raw")
    check("改名后磁盘跟随(内容仍可直读)", r.status_code == 200 and r.content == body)
    gone = all(c.delete(f"/api/file/{i}").status_code == 200 for i in (fid, hid, sid_))
    check("资料全删", gone)
    leftovers = [p.name for p in (settings.RESOURCES_DIR / "file").rglob("*.*")]
    check("盘净(先行后盘删干净)", not leftovers or print(leftovers))

    print("== E 其余可读面 ==")
    for url in ("/api/code/repos", "/api/projects", "/api/tech/list", "/api/diary/page"):
        check(f"GET {url} → 200", c.get(url).status_code == 200)

print(f"\n冒烟结果: {ok}/{n}")
sys.exit(0 if ok == n else 1)
