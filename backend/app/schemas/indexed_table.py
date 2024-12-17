from typing import Optional,List

from pydantic import UUID4, BaseModel
from datetime import datetime


# Shared properties
class IndexedTableBase(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    db_id: Optional[UUID4] = None
    synonyms: Optional[List[str]] = None
    sample_data: Optional[List[dict]] = None
    display_name: Optional[str] = None

# Properties to receive via API on creation
class IndexedTableCreate(IndexedTableBase):
    name: str
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



