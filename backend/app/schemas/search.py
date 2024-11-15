from typing import Optional,List
from pydantic import UUID4, BaseModel
from datetime import datetime


class TableInput(BaseModel):
    table_id: UUID4


class SearchInput(BaseModel):
    search_text: str    
    db_id: UUID4
    table_data: Optional[List[TableInput]] = None
    row_limit: Optional[int] = 50

# Shared properties
class SearchBase(BaseModel):
    input_search: Optional[SearchInput]
    search_type: Optional[str]


# Properties to receive via API on creation
class SearchCreate(SearchBase):
    input_search: SearchInput
    search_type: str 
    class Config:
        extra = "allow"


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

class RecentSearch(BaseModel):
    id: UUID4
    search_text: str

class SearchAutocomplete(BaseModel):
    search_text: str
