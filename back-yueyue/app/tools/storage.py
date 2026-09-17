"""统一磁盘存储工具(Java 视角:自己写的 MultipartFile 落地 + 资源定位器)。

photo / file(未来 videos)所有"上传落盘、删除销户、读盘应答"都走这一处,
业务层(service)只决定"该不该存/该不该删",怎么存安全全在这。

三条铁律:
  1. **入库只存相对 resources/ 的路径**("photo/20260916213045_k7fp.jpg",正斜杠),
     绝对路径永远不出 storage.py —— 换机器只改 settings.RESOURCES_DIR;
  2. **photo:文件名 = 时间戳 + "_" + 4 位随机字符 + 原扩展名**(去掉了易混字符 i l o 0 1),
     猜不到也撞不上,原始文件名另存 DB 的 name 列;
     **file(9/17 改口径):原文件名直接上盘**(safe_disk_name 清洗 + 撞名自动 "(N)" 避让),
     改名 = 磁盘同步 move,见 rename_saved —— 盘上所见即用户所命;
  3. **进出 resources/ 的相对路径一律过 jail()**(从 code_service 抽过来的公共生命线:
     拒 .. 段/绝对路径/盘符,resolve 后再验 is_relative_to,软链跳出也防住)。
"""
import secrets
import time
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.common.config.settings import REPOS_DIR, RESOURCES_DIR

# ---- 分类目录:category 就是 resources/ 下的子目录名,也是入库 path 的第一段 ----
CATEGORY_DIRS: dict[str, str] = {"photo": "photo", "file": "file"}

# ---- 尺寸上限:照片 20MB、资料 50MB(个人站口径,超了直接 413 不惯着) ----
MAX_BYTES: dict[str, int] = {
    "photo": 20 * 1024 * 1024,
    "file": 50 * 1024 * 1024,
}

# ---- 扩展名策略:photo 白名单(只收图),file 黑名单(挡可执行,别惯出钓鱼盘) ----
IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "webp", "bmp"}
FILE_EXT_BLACKLIST = {
    "exe", "bat", "cmd", "com", "scr", "msi", "msp", "jar",
    "sh", "ps1", "psm1", "vbs", "vbe", "js", "wsf", "hta", "lnk", "dll",
}

# ---- 图片魔数(前若干字节的签名):后缀可以骗人,文件头不能 ----
_MAGIC_CHECKS = {
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "gif": [b"GIF87a", b"GIF89a"],
    "bmp": [b"BM"],
    # webp 特殊:RIFF????WEBP,中间 4 字节是长度,拆开验
}

_RANDOM_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # 去易混字符
_CHUNK = 1024 * 1024  # 1MB 分块搬运,不把整文件吸进内存


def jail(root: Path, rel: str) -> Path:
    """相对路径 → 磁盘目标,越狱即 400(全站唯一的路径生命线)。

    防四样:绝对路径(F:\\ / /etc)、.. 段逃逸、盘符混进相对段、符号链接跳出。
    顺序必须"先清洗再 resolve 再 is_relative_to" —— resolve 把 .. 和软链都折叠掉,
    折叠完还在 root 里才算合法(Java 类比:normalize + startsWith,但 normalize 不够,
    软链要 real path 才能防住)。

    原实现长在 code_service._jail,9/16 抽到这里两处共用(代码浏览器 + 上传文件区)。
    """
    rel = (rel or "").replace("\\", "/").strip("/")
    parts = rel.split("/")
    if not rel or any(p in ("", ".", "..") for p in parts) or ":" in rel:
        raise HTTPException(status_code=400, detail="非法路径")
    root_real = root.resolve()
    target = (root_real / rel).resolve()
    if not target.is_relative_to(root_real):
        raise HTTPException(status_code=400, detail="非法路径")
    return target


def resolve_saved(rel_path: str) -> Path:
    """DB 里的相对路径 → 磁盘绝对路径(读盘应答用;文件在不在调用方自己判)。"""
    return jail(RESOURCES_DIR, rel_path)


# ---- 仓库路径("在线看代码"挂载的本机目录,9/17 口径统一):和照片同款纪律,
# 库里只存相对 REPOS_DIR 的正斜杠路径,绝对根只活在这两个函数里 ----

def normalize_repo_path(raw: str) -> str:
    """写入口径化:空→"";相对路径清洗(拒 .. 逃逸);绝对路径在 REPOS_DIR 下自动改写。

    绝对路径不再原样入库 —— 换机器时它就是 DB 里的一枚哑弹。
    """
    raw = (raw or "").strip().replace("\\", "/")
    if not raw:
        return ""
    root_real = REPOS_DIR.resolve()
    p = Path(raw)
    if p.is_absolute():
        try:
            rel = p.resolve().relative_to(root_real)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"只能挂 {root_real} 下的目录:把仓库挪进去,或填相对路径")
    else:
        parts = [seg for seg in raw.split("/") if seg not in ("", ".")]
        if any(seg == ".." for seg in parts) or ":" in raw:
            raise HTTPException(status_code=400, detail="非法路径")
        try:  # resolve 后仍要验归属:软链能把相对路径带出根外(和 jail 同一手)
            rel = (root_real / "/".join(parts)).resolve().relative_to(root_real)
        except ValueError:
            raise HTTPException(status_code=400, detail="非法路径")
    if not rel.parts:
        raise HTTPException(status_code=400, detail="别把根目录本身挂成仓库")
    return rel.as_posix()


def repo_root(stored: str) -> Path:
    """DB path 列 → 本机仓库目录。

    正身是相对 REPOS_DIR;旧行绝对路径(9/17 口径前入库的)照原样可读,
    下次编辑保存时经 normalize_repo_path 自动归正。
    """
    p = Path((stored or "").replace("\\", "/"))
    return p if p.is_absolute() else REPOS_DIR / p


def _category_dir(category: str) -> Path:
    sub = CATEGORY_DIRS.get(category)
    if sub is None:
        raise ValueError(f"未知存储分类:{category}(要在 CATEGORY_DIRS 里登记)")
    root = RESOURCES_DIR / sub
    root.mkdir(parents=True, exist_ok=True)  # 首用自建,不靠手工摆目录
    return root


def _tail(filename: str) -> str:
    """浏览器传来的文件名可能带全路径(IE 系 "C:\\fakepath\\" 惯性),只留最后一段。"""
    return (filename or "").replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]


def original_name(filename: str) -> str:
    """入库展示用的原始文件名:去路径 + 去控制字符 + 截到 255(列宽)。

    ⚠️ 只当"标签"用(展示/下载名),永远不参与拼盘路径 —— 盘上名字归 _new_name 管。
    """
    name = "".join(c for c in _tail(filename) if c.isprintable()).strip()
    return name[:255]


def _ext_of(filename: str) -> str:
    """原始文件名 → 小写扩展名(不带点);无扩展名返回空串。"""
    fn = _tail(filename)
    return fn.rsplit(".", 1)[-1].lower() if "." in fn else ""


# Windows 保留设备名:不管扩展名,主名撞上就废(资源管理器里根本建不出来)
_WIN_RESERVED = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10)),
}
# 文件名里的非法/高危字符:路径分隔和注入全靠 jail/清洗挡,这些直接抹掉
_FORBID_CHARS = set('<>:"/\\|?*')


def safe_disk_name(raw: str) -> str:
    """任意用户输入的文件名 → 能直接落盘的安全文件名;清洗到什么都不剩则回 ""。

    file 分类"原名上盘"口径的第一道闸(上传和改名共用):
    去路径、去控制字符、去 Windows 非法字符、首尾点和空格显式清掉
    (否则 NTFS 尾部静默截断,盘上名字和 DB 对不上)、保留名加下划线、截到 120。
    """
    name = "".join(c for c in _tail(raw or "") if c.isprintable() and c not in _FORBID_CHARS)
    name = name.strip().strip(".").strip()
    if not name:
        return ""
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    if stem.lower() in _WIN_RESERVED:
        stem = "_" + stem
    if len(name) > 120:
        stem = stem[: max(1, 120 - len(ext) - (1 if dot else 0))]
    return f"{stem}.{ext}" if dot and ext else stem


def _unique(root: Path, name: str) -> str:
    """目录里重名 → "stem(1).ext" 递增避让。上传用(改名不用,那边直接 400)。"""
    if not (root / name).exists():
        return name
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    i = 1
    cand = name
    while (root / cand).exists():
        cand = f"{stem}({i}).{ext}" if ext else f"{stem}({i})"
        i += 1
    return cand


def rename_saved(old_rel: str, clean_name: str) -> str:
    """改名的磁盘侧:同目录 move,返回新入库路径(调用方负责同步 DB 的 path/name)。

    撞名直接 400 不自动编号 —— 改名是明确意图,悄悄变成 "xxx(1)" 只会让人找不到文件;
    (上传撞名才自动编号,那叫批量不叫意图。)
    """
    old = resolve_saved(old_rel)
    if not old.is_file():
        raise HTTPException(status_code=400, detail="磁盘上的文件不见了,无法改名")
    new = old.with_name(clean_name)
    if new.exists():
        raise HTTPException(status_code=400, detail=f"已有同名文件:{clean_name}")
    old.rename(new)
    return f"{old_rel.split('/', 1)[0]}/{clean_name}"


def _check_magic(head: bytes, ext: str) -> None:
    """图片类别的落盘前置校验:后缀声称是图,文件头得认账(假图 400 拒)。"""
    if ext == "webp":
        if not (head[:4] == b"RIFF" and head[8:12] == b"WEBP"):
            raise HTTPException(status_code=400, detail="文件内容与扩展名不符,拒收")
        return
    sigs = _MAGIC_CHECKS.get(ext)
    if sigs and not any(head.startswith(s) for s in sigs):
        raise HTTPException(status_code=400, detail="文件内容与扩展名不符,拒收")


def _new_name(ext: str) -> str:
    """时间戳+4位随机字符(用户钦定命名);ext 不带点,无扩展名就留空后缀。"""
    ts = time.strftime("%Y%m%d%H%M%S")
    rand = "".join(secrets.choice(_RANDOM_ALPHABET) for _ in range(4))
    return f"{ts}_{rand}.{ext}" if ext else f"{ts}_{rand}"


async def save(
    category: str,
    upload: UploadFile,
    *,
    allowed_exts: set[str] | None = None,
    blacklisted_exts: set[str] | None = None,
    magic_check: bool = False,
    keep_original_name: bool = False,
) -> tuple[str, int]:
    """UploadFile → 落盘,返回 (相对 resources/ 的入库路径, 字节数)。

    校验链:分类登记 → 扩展名白/黑名单 → 分块写盘(顺带验总大小)→ 图片魔数复核。
    任何一步不合格:400/413 抛出去,已写的半个文件当场删掉,绝不留半成品。
    """
    root = _category_dir(category)
    max_bytes = MAX_BYTES[category]
    ext = _ext_of(upload.filename or "")

    if allowed_exts is not None and ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型{('.' + ext) if ext else '(无扩展名)'},"
            f"只接收:{'/'.join(sorted(allowed_exts))}",
        )
    if blacklisted_exts is not None and ext in blacklisted_exts:
        raise HTTPException(status_code=400, detail=f"可执行类文件(.{ext})拒收")

    if keep_original_name:
        # file 分类口径:原名直接上盘(safe_disk_name 清洗 + "(N)" 避让撞名)
        base = safe_disk_name(upload.filename or "")
        name = _unique(root, base) if base else _new_name(ext)  # 全非法原名 → 退回随机兜底
    else:
        # 时间戳精度到秒,理论上同秒可撞名;随机 4 位 + 重掷循环兜底
        name = _new_name(ext)
    target = root / name
    while target.exists():
        name = _new_name(ext)
        target = root / name

    written = 0
    try:
        with target.open("wb") as fh:
            while chunk := await upload.read(_CHUNK):
                # 首块落盘**前**先验魔数:假图一个字节都不许留在 resources/ 里
                if magic_check and written == 0:
                    _check_magic(chunk[:16], ext)
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"文件超过上限 {max_bytes // (1024 * 1024)}MB",
                    )
                fh.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)  # 半途而废就当场销尸,不留孤儿
        raise
    finally:
        await upload.close()

    if written == 0:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="空文件,不收")

    # 入库路径:相对 resources/ 且永远正斜杠(Windows 反斜杠不许进 DB)
    return f"{CATEGORY_DIRS[category]}/{name}", written


def delete(rel_path: str) -> bool:
    """按入库路径销户:删了返回 True;文件本就不在返回 False(幂等,不炸)。

    调用时机由业务层定死:**DB 行删成功之后**才允许删盘 ——
    指针永远比文件活得久,反序会留下"库里查不到、盘上见不得人"的孤儿文件。
    """
    target = resolve_saved(rel_path)
    if not target.is_file():
        return False
    target.unlink()
    return True
