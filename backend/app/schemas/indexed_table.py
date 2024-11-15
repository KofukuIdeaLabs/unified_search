from typing import Optional

from pydantic import UUID4, BaseModel
from datetime import datetime


# Shared properties
class IndexedTableBase(BaseModel):
    name: Optional[str]
    description: Optional[str]
    db_id: Optional[UUID4]


# Properties to receive via API on creation
class IndexedTableCreate(IndexedTableBase):
    name: str
    description: str
    db_id: UUID4


# Properties to receive via API on update
class IndexedTableUpdate(IndexedTableBase):
    pass


class IndexedTableInDBBase(IndexedTableBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# Additional properties to return via API
class IndexedTable(IndexedTableInDBBase):
    pass


class IndexedTableInDB(IndexedTableInDBBase):
    pass



