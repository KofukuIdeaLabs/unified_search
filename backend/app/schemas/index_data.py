from typing import Optional
from fastapi import UploadFile
from pydantic import UUID4, BaseModel
from datetime import datetime


# Shared properties
class IndexDataBase(BaseModel):
    file: UploadFile | None = None
    db_id: Optional[UUID4] = None
    table_name: Optional[str] = None


# Properties to receive via API on creation
class IndexDataCreate(IndexDataBase):
    file: UploadFile
    db_id: UUID4


# Properties to receive via API on update
class IndexDataUpdate(IndexDataBase):
    pass


class IndexDataInDBBase(IndexDataBase):
    pass

    class Config:
        orm_mode = True


# Additional properties to return via API
class IndexData(IndexDataInDBBase):
    pass


class IndexDataInDB(IndexDataInDBBase):
    pass



