"""统一的新内容可见性口径，避免前端继续暴露 role=0/1。"""

def visibility_to_role(value: str) -> int:
    if value not in ("public", "private"):
        raise ValueError("visibility must be public or private")
    return 1 if value == "private" else 0


def role_to_visibility(role: int) -> str:
    return "private" if role == 1 else "public"
