from fastapi import APIRouter

from app.common.config.config import API_PREFIX

router = APIRouter(prefix=f"{API_PREFIX}/photo", tags=["diary"])

async def page_photo_api(
    page: int = 1,
    page_size: int = 10,
    role: int = 0,
    path: str = "",
    create_at: str = ""
):
    total,rows = await