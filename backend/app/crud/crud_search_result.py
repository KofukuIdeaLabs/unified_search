from typing import Any, Dict, List, Union, Optional
from app.crud.base import CRUDBase
from sqlalchemy.orm import Session
from app.models.search_result import SearchResult
from app.schemas.search_result import SearchResultCreate, SearchResultUpdate
from pydantic.types import UUID4
from app.models.search import Search

class CRUDSearchResult(CRUDBase[SearchResult, SearchResultCreate, SearchResultUpdate]):
    def get_result_by_search_id(self, db: Session, *, search_id: UUID4):
        return (
            db.query(
                self.model.created_at,
                self.model.updated_at,
                Search.input_search['search_text'].label('search_text'),
                self.model.search_id.label("id"),
                self.model.result,
                self.model.rating,
                self.model.is_satisfied,
                Search.search_type.label('search_type'),
                self.model.extras
            )
            .join(Search, SearchResult.search_id == Search.id)
            .filter(
                SearchResult.search_id == search_id,
            )
            .first()
        )


search_result = CRUDSearchResult(SearchResult)