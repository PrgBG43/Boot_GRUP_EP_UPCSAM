from typing import Optional

from pydantic import BaseModel


class CityBase(BaseModel):
    name: str
    state_id: int


class CityCreate(CityBase):
    pass


class CityUpdate(BaseModel):
    name: Optional[str] = None
    state_id: Optional[int] = None


class CityResponse(CityBase):
    id: int

    class Config:
        from_attributes = True
