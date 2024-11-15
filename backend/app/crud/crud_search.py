from typing import List
from app.crud.base import CRUDBase
from app.models.search import Search
from app.schemas.search import SearchCreate, SearchUpdate
from sqlalchemy.orm import Session
from pydantic.types import UUID4
from app.models.search_result import SearchResult


class CRUDSearch(CRUDBase[Search, SearchCreate, SearchUpdate]):
    def get_multi_by_user_id(
        self,
        db: Session,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Search]:
        return (
            db.query(self.model)
            .filter(Search.user_id == user_id)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_search_count(self, db: Session, *, user_id: int):
        return db.query(self.model).filter(Search.user_id == user_id).count()

    def get_search_results(
        self,
        db: Session,
        *,
        search_id: UUID4,
    ):
        return db.query(SearchResult).filter(SearchResult.search_id == search_id).all()


search = CRUDSearch(Search)