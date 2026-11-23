from pydantic import BaseModel, ConfigDict


class AreaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    name_bn: str
