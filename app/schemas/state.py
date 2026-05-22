from typing import Optional

from pydantic import BaseModel, field_validator


class StateBase(BaseModel):
    description: str
    code: Optional[str] = None

    @field_validator('description', mode='before')
    @classmethod
    def _alias_name(cls, v):
        return v


class StateCreate(StateBase):
    pass


class StateUpdate(BaseModel):
    description: Optional[str] = None
    code: Optional[str] = None


class StateResponse(StateBase):
    id: int

    class Config:
        from_attributes = True

