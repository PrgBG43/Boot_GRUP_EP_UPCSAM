from typing import Optional

from pydantic import BaseModel


class CityBase(BaseModel):
    description: str
    code: Optional[str] = None
    state_id: int


class CityCreate(CityBase):
    pass


class CityUpdate(BaseModel):
    description: Optional[str] = None
    code: Optional[str] = None
    state_id: Optional[int] = None


class CityResponse(CityBase):
    id: int

    class Config:
        from_attributes = True

