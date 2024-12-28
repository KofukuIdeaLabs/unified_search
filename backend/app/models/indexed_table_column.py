from typing import TYPE_CHECKING
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
import datetime
from uuid import uuid4
from app.db.base_class import Base
from sqlalchemy.ext.mutable import MutableDict

if TYPE_CHECKING:
    pass


class IndexedTable(Base):
    __tablename__ = "indexed_table"


    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        index=True,
        default=uuid4,
    )
    name = Column(String, index=True)
    display_name = Column(String)
    description = Column(String)
    synonyms = Column(ARRAY(String))
    db_id = Column(UUID(as_uuid=True), ForeignKey("indexed_db.id"))
    sample_data = Column(ARRAY(JSONB))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )
    attributes_to_retrieve = Column(JSONB, default=dict)
    relationship_with_other_index = Column(MutableDict.as_mutable(JSONB), nullable=True)
    access_to_roles = Column(ARRAY(UUID(as_uuid=True)), default=list)
    deleted_at = Column(DateTime)
