from typing import Optional,List,Any

from pydantic import UUID4, BaseModel
from datetime import datetime


# Shared properties
class IndexedTableColumnBase(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    db_id: Optional[UUID4] = None
    synonyms: Optional[List[str]] = None
    unique_values: Optional[Any] = None


# Properties to receive via API on creation
class IndexedTableColumnCreate(IndexedTableColumnBase):
    name: str
    db_id: UUID4


# Properties to receive via API on update
class IndexedTableColumnUpdate(IndexedTableColumnBase):
    pass


class IndexedTableColumnInDBBase(IndexedTableColumnBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# Additional properties to return via API
class IndexedTableColumn(IndexedTableColumnInDBBase):
    pass


class IndexedTableColumnInDB(IndexedTableColumnInDBBase):
    pass



