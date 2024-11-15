from typing import Optional

from pydantic import UUID4, BaseModel
from datetime import datetime


# Shared properties
class IndexedDBBase(BaseModel):
    name: Optional[str]
    description: Optional[str]


# Properties to receive via API on creation
class IndexedDBCreate(IndexedDBBase):
    name: str
    description: str


# Properties to receive via API on update
class IndexedDBUpdate(IndexedDBBase):
    pass


class IndexedDBInDBBase(IndexedDBBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# Additional properties to return via API
class IndexedDB(IndexedDBInDBBase):
    pass


class IndexedDBInDB(IndexedDBInDBBase):
    pass



