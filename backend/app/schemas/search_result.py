from typing import Optional,List
from pydantic import UUID4, BaseModel
from datetime import datetime


class SearchResultFormat(BaseModel):
    table_name:str
    result_data:List

# Shared properties
class SearchResultBase(BaseModel):
    result: Optional[List[SearchResultFormat]]=[]
    rating: Optional[int]=None
    is_satisfied: Optional[bool]=None
    search_id: Optional[UUID4]=None


# Properties to receive via API on creation
class SearchResultCreate(SearchResultBase):
    result: List[SearchResultFormat]
    search_id: UUID4


# Properties to receive via API on update
class SearchResultUpdate(SearchResultBase):
    pass


class SearchResultInDBBase(SearchResultBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime


    class Config:
        orm_mode = True


# Additional properties to return via API
class SearchResult(SearchResultInDBBase):
    pass


class SearchResultInDB(SearchResultInDBBase):
    pass


