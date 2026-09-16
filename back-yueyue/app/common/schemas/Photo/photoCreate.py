from pydantic import BaseModel


class PhotoCreateSchema(BaseModel):
    type: str
    role: int
    path: str

