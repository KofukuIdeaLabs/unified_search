from typing import Any, Dict, List, Optional, Union

from app.core.security import get_password_hash, verify_password
from app.crud.base import CRUDBase
from app.models import AppUser, Role
from app.schemas.app_user import AppUserCreate, AppUserUpdate
from pydantic.types import UUID4
from sqlalchemy.orm import Session, defer
from app.crud.crud_role import role

from app.constants.role import Role as ConstantsRole


class CRUDAppUser(CRUDBase[AppUser, AppUserCreate, AppUserUpdate]):

    def get_by_email(self, db: Session, *, email: str) -> Optional[AppUser]:
        return db.query(self.model).filter(AppUser.email == email).first()
    
    def get_with_roles(self, db: Session, *, id: UUID4) -> Optional[AppUser]:
        return db.query(self.model.created_at,self.model.updated_at,self.model.email,self.model.full_name,self.model.is_active,self.model.org_id,Role.name).join(Role,Role.id == self.model.role_id).filter(self.model.id == id).first()

    def create(self, db: Session, *, obj_in: AppUserCreate) -> AppUser:
        if not obj_in.role_id:
            member_role = role.get_by_name(db, name=ConstantsRole.MEMBER["name"])
            obj_in.role_id = member_role.id
        db_obj = AppUser(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            # full_name=obj_in.full_name,
            role_id=obj_in.role_id,
            org_id=obj_in.org_id,
            is_active=obj_in.is_active,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: AppUser,
        obj_in: Union[AppUserUpdate, Dict[str, Any]],
    ) -> AppUser:
        #
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
            # print(update_data)
        if "password" in update_data:
            hashed_password = get_password_hash(update_data["password"])
            # print(hashed_password)
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
        # print(update_data)
        return super().update(db, db_obj=db_obj, obj_in=update_data)

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AppUser]:
        return db.query(self.model).offset(skip).limit(limit).all()

    def authenticate(self, db: Session, *, email: str, password: str) -> Optional[AppUser]:
        # print(email)
        user = self.get_by_email(db, email=email)
        # print(user.id)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            # print(user.hashed_password)
            return None
        return user

    def is_active(self, user: AppUser) -> bool:
        return user.is_active

    def get_by_account_id_all(
        self,
        db: Session,
        *,
        account_id: UUID4,
    ) -> List[AppUser]:
        return db.query(self.model).filter(AppUser.id == account_id).all()

    def get_team_members_count_by_account_id(
        self,
        db: Session,
        *,
        account_id: UUID4,
    ):
        return db.query(self.model).filter(AppUser.account_id == account_id).count()

    def get_users_by_org_id(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        org_id: UUID4,
    ):
        return (
            db.query(AppUser).filter(AppUser.org_id == org_id).offset(skip).limit(limit).all()
        )

    def get_user_id_from_user_name(self, db: Session, user_name: str):
        return db.query(AppUser).filter(AppUser.full_name == user_name).one()

    def get_org_id_from_user_id(self, db: Session, user_id: UUID4):
        return db.query(AppUser).filter(AppUser.id == user_id).one()


app_user = CRUDAppUser(AppUser)
