from pydantic import BaseModel


class photoUpdate(BaseModel):
    type: str
    role: int