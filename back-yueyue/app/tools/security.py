"""密码哈希(Java 视角:Spring Security 的 BCryptPasswordEncoder,这里用标准库版)。

- 用 hashlib.pbkdf2_hmac:Python 自带,不用引第三方依赖;
  120000 次迭代 = 故意算得慢,让拖库的人暴力破解贵(≈ BCrypt 的 strength)。
- 存储格式一串自描述:`算法$迭代数$盐$哈希`,以后想调迭代数,
  老密文照样能按自己那行参数复算,不用全库重置。
- 比对必须走 hmac.compare_digest(定长时间),普通 == 会留时序侧信道。
"""
import hashlib
import hmac
import secrets

_ALGORITHM = "sha256"
_ITERATIONS = 120_000


def hash_password(plain: str) -> str:
    """明文 → 入库字符串。每人随机盐:同密码两人存出来不一样。"""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(_ALGORITHM, plain.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS)
    return f"{_ALGORITHM}${_ITERATIONS}${salt}${digest.hex()}"


def verify_password(plain: str, stored: str) -> bool:
    """明文 + 库里那串 → 是否匹配;格式不对/没存过一律 False。"""
    try:
        algorithm, iterations, salt, expected = stored.split("$")
        digest = hashlib.pbkdf2_hmac(
            algorithm, plain.encode("utf-8"), bytes.fromhex(salt), int(iterations)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), expected)
