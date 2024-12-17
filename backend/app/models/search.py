from typing import TYPE_CHECKING
from sqlalchemy import Column, ForeignKey, DateTime, String
from app.db.base_class import Base
import datetime
from sqlalchemy.dialects.postgresql import UUID, JSON, JSONB
from uuid import uuid4
from sqlalchemy.orm import relationship
from sqlalchemy_json import mutable_json_type
from app.constants.search_type import SearchType
if TYPE_CHECKING:
    from .app_user import AppUser


class Search(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    input_search = Column(mutable_json_type(dbtype=JSONB, nested=True), default={})
    user_id = Column(UUID(as_uuid=True), ForeignKey("app_user.id"))
    search_type = Column(String, default=SearchType.TERM)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    deleted_at = Column(DateTime, default=None)
