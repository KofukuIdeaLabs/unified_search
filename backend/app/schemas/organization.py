from datetime import datetime
from typing import Optional

from pydantic import UUID4, BaseModel


# Shared properties
class OrganizationBase(BaseModel):
    name: Optional[str]
    description: Optional[str]
    is_active: Optional[bool] = True


# Properties to receive via API on creation
class OrganizationCreate(OrganizationBase):
    name: str
    description: str


# Properties to receive via API on update
class OrganizationUpdate(OrganizationBase):
    class Config:
        orm_mode = True


class OrganizationRemove(OrganizationBase):
    id: UUID4
    deleted_at: datetime

    class Config:
        orm_mode = True


class OrganizationInDBBase(OrganizationBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# Additional properties to return via API
class Organization(OrganizationInDBBase):
    pass


class OrganizationInDB(OrganizationInDBBase):
    pass
