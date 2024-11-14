from typing import Any, Dict, List, Optional, Union

from app.crud.base import CRUDBase
from app.models.organization import Organization
from app.schemas.organization import OrganizationCreate, OrganizationUpdate
from sqlalchemy.orm import Session

from pydantic.types import UUID4


class CRUDOrganization(CRUDBase[Organization, OrganizationCreate, OrganizationUpdate]):
    def get_by_name(self, db: Session, *, name: str) -> Optional[Organization]:
        return db.query(self.model).filter(Organization.name == name).first()

    def is_active(self, Organization: Organization) -> bool:
        return Organization.is_active

    def get_by_id(self, db: Session, *, id: str) -> Optional[Organization]:
        return db.query(self.model).filter(Organization.id == id).first()


organization = CRUDOrganization(Organization)
