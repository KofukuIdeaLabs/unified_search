from typing import TYPE_CHECKING
from sqlalchemy import Column, ForeignKey, DateTime, String, Integer, Boolean
from app.db.base_class import Base
import datetime
from sqlalchemy.dialects.postgresql import UUID, JSON, JSONB
from uuid import uuid4
from sqlalchemy.orm import relationship
from sqlalchemy_json import mutable_json_type
from app.constants.search_type import SearchType
if TYPE_CHECKING:
    from .search import Search


class SearchResult(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    search_id = Column(UUID(as_uuid=True), ForeignKey("search.id"))
    result = Column(mutable_json_type(dbtype=JSONB, nested=True), default={})
    rating = Column(Integer, default=0)
    is_satisfied = Column(Boolean, default=None)
    extras = Column(mutable_json_type(dbtype=JSONB, nested=True), default={})
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    deleted_at = Column(DateTime, default=None)
