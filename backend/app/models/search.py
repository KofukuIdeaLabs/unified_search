from typing import TYPE_CHECKING
from sqlalchemy import Text, JSON, Integer, Column, ForeignKey, DateTime, JSON, Float
from app.db.base_class import Base
import datetime
from sqlalchemy.dialects.postgresql import UUID, JSON, JSONB
from uuid import uuid4
from sqlalchemy.orm import relationship
from sqlalchemy_json import mutable_json_type

if TYPE_CHECKING:
    from .searchresult import SearchResult  # noqa: F401
    from .share import Share
    from .pipeline import Pipeline


class Search(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("appuser.id"))
    input_search = Column(mutable_json_type(dbtype=JSONB, nested=True), default={})
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    deleted_at = Column(DateTime, default=None)
