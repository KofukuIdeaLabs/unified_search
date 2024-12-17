from typing import TYPE_CHECKING
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
import datetime
from uuid import uuid4
from app.db.base_class import Base

if TYPE_CHECKING:
    pass


class AppUser(Base):
    __tablename__ = "app_user"


    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        index=True,
        default=uuid4,
    )
    full_name = Column(String(255), index=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )
    deleted_at = Column(DateTime)
    role_id = Column(UUID(as_uuid=True), ForeignKey("role.id"))
    org_id = Column(UUID(as_uuid=True), ForeignKey("organization.id"))