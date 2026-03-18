from typing import Optional

from pydantic import BaseModel


class PermissionBase(BaseModel):
    name: str
    description: Optional[str] = None


class PermissionCreate(PermissionBase):
    pass


class PermissionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class PermissionResponse(PermissionBase):
    id: int

    class Config:
        from_attributes = True
