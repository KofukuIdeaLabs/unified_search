from __future__ import annotations
from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    ARRAY,
)
from sqlalchemy.orm import relationship, Mapped , mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict, MutableList
from app.db.base_class import Base
from datetime import datetime
from typing import Optional, TYPE_CHECKING , List
from sqlalchemy.dialects.postgresql import UUID, JSON, JSONB
from uuid import uuid4

if TYPE_CHECKING:
    from .app_user import AppUser
    from .police_case import PoliceCase
    from .act_section import ActSection
    from .status_report import StatusReport


class FormInstance(Base):
    __tablename__ = "form_instance"

    
     


    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
    )
    name = Column(String,nullable=False)
    form = Column(MutableList.as_mutable(JSONB), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)
    responses = Column(MutableDict.as_mutable(JSONB), nullable=True)
    deleted_at = Column(DateTime, default=None, nullable=True)
    owner_id = Column(UUID(as_uuid=True),ForeignKey("app_user.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("form_template.id"), nullable=False)