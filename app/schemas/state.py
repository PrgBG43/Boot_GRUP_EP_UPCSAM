from typing import Optional

from pydantic import BaseModel


class StateBase(BaseModel):
    name: str


class StateCreate(StateBase):
    pass


class StateUpdate(BaseModel):
    name: Optional[str] = None


class StateResponse(StateBase):
    id: int

    class Config:
        from_attributes = True
