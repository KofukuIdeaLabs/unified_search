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
    extras: Optional[dict] = None # right now the architecute is in between the old and new project so need to add extra data here


# Properties to receive via API on creation
class SearchResultCreate(SearchResultBase):
    search_id: UUID4


# Properties to receive via API on update
class SearchResultUpdate(SearchResultBase):
    pass


class SearchResultInDBBase(SearchResultBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime
    search_text: str
    status: str


    class Config:
        orm_mode = True


# Additional properties to return via API
class SearchResult(SearchResultInDBBase):
    pass


class SearchResultInDB(SearchResultInDBBase):
    pass




