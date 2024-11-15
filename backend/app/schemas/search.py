from typing import Optional
from pydantic import UUID4, BaseModel
from datetime import datetime


class SearchInput(BaseModel):
    search_text: str    
    table_names: list[str]
    db_name: str

# Shared properties
class SearchBase(BaseModel):
    input_search: Optional[SearchInput]
    search_type: Optional[str]


# Properties to receive via API on creation
class SearchCreate(SearchBase):
    input_search: SearchInput
    search_type: str 


# Properties to receive via API on update
class SearchUpdate(SearchBase):
    pass


class SearchInDBBase(SearchBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime


    class Config:
        orm_mode = True


# Additional properties to return via API
class Search(SearchInDBBase):
    pass


class SearchInDB(SearchInDBBase):
    pass


class ListSearch(BaseModel):
    name: str

    class Config:
        orm_mode = True

class SearchId(BaseModel):
    id:UUID4