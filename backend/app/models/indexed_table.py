from typing import TYPE_CHECKING
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
import datetime
from uuid import uuid4
from app.db.base_class import Base

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
    description = Column(String)
    db_id = Column(UUID(as_uuid=True), ForeignKey("indexed_db.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )
    deleted_at = Column(DateTime)
