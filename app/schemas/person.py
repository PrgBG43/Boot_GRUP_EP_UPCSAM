from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PersonBase(BaseModel):
    first_name: str
    last_name: str
    phone: Optional[str] = None
    city_id: Optional[int] = None


class PersonCreate(PersonBase):
    pass


class PersonUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    city_id: Optional[int] = None


class PersonResponse(PersonBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
