from __future__ import annotations
from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict, MutableList
from app.db.base_class import Base
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy.dialects.postgresql import UUID, JSON, JSONB
from uuid import uuid4

if TYPE_CHECKING:
    from .organization import Organization
    from .app_user import AppUser


class FormTemplate(Base):
    __tablename__ = "form_template"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name= Column(String,nullable=True)
    description = Column(String,nullable=True)
    template = Column(MutableList.as_mutable(JSONB), nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    extras = Column(MutableDict.as_mutable(JSONB), nullable=True)
    organization_id = Column(ForeignKey("organization.id"), nullable=False)
    owner_id = Column(ForeignKey("app_user.id"), nullable=False)
    deleted_at = Column(DateTime, default=None, nullable=True)