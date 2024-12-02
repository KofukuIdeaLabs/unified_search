from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, EmailStr, UUID4


# Shared properties
class AppUserBase(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = False
    full_name: Optional[str] = None
    org_id: Optional[UUID4]
    role_id: Optional[UUID4]


# Properties to receive via API on creation
class AppUserCreate(AppUserBase):
    email: EmailStr
    password: str
    role_id: UUID4
    org_id: UUID4
    full_name: str


# Properties to receive via API on update
class AppUserUpdate(AppUserBase):
    email_verified: Optional[bool] = False
    password: Optional[str] = None
    personal_workspace_id: Optional[UUID4]


class AppUserInDBBase(AppUserBase):
    id: UUID4
    created_at: datetime
    # updated_at: datetime

    class Config:
        orm_mode = True


class AppUserRemove(AppUserBase):
    id: UUID4
    deleted_at: datetime

    class Config:
        orm_mode = True



# Additional properties to return via API
class AppUser(AppUserInDBBase):
    class Config:
        orm_mode = True


# Additional properties stored in DB
class AppUserInDB(AppUserInDBBase):
    hashed_password: str

class AppUserPublic(BaseModel):
    id: UUID4
    email: EmailStr
    full_name: str
    role_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True