from typing import Optional,List,Dict,Any
from pydantic import UUID4, BaseModel,Field
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

class PaginationInfo(BaseModel):
    offset: int
    limit: int
    total_hits: Optional[int] = None


class SearchResultInDBBase(SearchResultBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime
    search_text: str
    status: str = "pending"
    @property
    def pagination(self) -> Optional[PaginationInfo]:
        if self.extras and "pagination" in self.extras:
            return PaginationInfo(**self.extras["pagination"])
        return None


    class Config:
        orm_mode = True


# Additional properties to return via API
class SearchResult(SearchResultInDBBase):
    pass


class SearchResultInDB(SearchResultInDBBase):
    pass




