from typing import Optional,List,Dict,Any
from pydantic import UUID4, BaseModel,Field
from datetime import datetime



class PaginationInfo(BaseModel):
    skip: int
    limit: int


class SearchResultFormat(BaseModel):
    table_name:str
    result_data:List
    table_id:Optional[UUID4]=None
    pagination:Optional[PaginationInfo]=None
    total_hits:Optional[int]=None
    display_name: Optional[str] = None


# Shared properties
class SearchResultBase(BaseModel):
    result: Optional[List[SearchResultFormat]]=None
    rating: Optional[int]=None
    is_satisfied: Optional[bool]=None
    search_id: Optional[UUID4]=None
    extras: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Additional data including pagination info"
    )



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
    status: str = "pending"

    class Config:
        orm_mode = True


# Additional properties to return via API
class SearchResult(SearchResultInDBBase):
    pass


class SearchResultInDB(SearchResultInDBBase):
    pass




