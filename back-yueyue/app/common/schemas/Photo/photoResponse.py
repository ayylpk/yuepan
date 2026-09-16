from pydantic import BaseModel, ConfigDict


class PhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:int
    type:str
    role:int
    path:str
    created_at:str