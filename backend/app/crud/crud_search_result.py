from typing import Any, Dict, List, Union, Optional
from app.crud.base import CRUDBase
from sqlalchemy.orm import Session
from app.models.search_result import SearchResult
from app.schemas.search_result import SearchResultCreate, SearchResultUpdate
from pydantic.types import UUID4


class CRUDSearchResult(CRUDBase[SearchResult, SearchResultCreate, SearchResultUpdate]):
    def get_results_by_search_id(self, db: Session, *, search_id: UUID4):
        return (
            db.query(self.model)
            .filter(
                SearchResult.search_id == search_id,
            )
            .all()
        )


search_result = CRUDSearchResult(SearchResult)