from typing import Optional,List
from pydantic import UUID4, BaseModel
from datetime import datetime
from typing import Union,Any




class GenerateUserQueryInput(BaseModel):
    data: List[dict]


# class GenerateUserQueryOutput(BaseModel):
#     query: str


class GeneratePromptOutput(BaseModel):
    type: str
    data: str


class GeneratePromptOutputResponse(BaseModel):
    result: List[GeneratePromptOutput]





class SearchInput(BaseModel):
    query: Any    
    db_id: UUID4
    
    table_ids: Optional[List[UUID4]] = []
    row_limit: Optional[int] = 50
    exact_match: Optional[bool] = False
    optimize_search: Optional[bool] = False

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

# class QueryOnData(BaseModel):
#     data: dict
#     original_user_query:str
#     table_ids
#     columns: List[str]
#     table_name: str
#     tables_to_query:List[dict]
#     database_to_query: str
#     row_limit: int
#     original_query:str
