import uuid
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from app import crud,schemas,models
from sqlalchemy.orm import Session
from app.api import deps
from app.core.config import settings
from app.core.security import get_password_hash, verify_password


router = APIRouter()


@router.get("", response_model=List[schemas.AppUser])
def read_users(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.AppUser = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve all users.
    """
    users = crud.app_user.get_multi(db, skip=skip, limit=limit)
    return users


@router.post(
    "/", dependencies=[Depends(deps.get_current_active_superuser)], response_model=schemas.AppUser
)
def create_user(*, db: Session = Depends(deps.get_db), user_in: schemas.AppUserCreate) -> Any:
    """
    Create new user.
    """
    user = crud.app_user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    user = crud.app_user.create(db, obj_in=user_in)
    return user


@router.patch("/me", response_model=schemas.AppUser)
def update_user_me(
    *, db: Session = Depends(deps.get_db), user_in: schemas.AppUserUpdate, current_user: deps.CurrentActiveUser
) -> Any:
    """
    Update own user.
    """

    if user_in.email:
        existing_user = crud.app_user.get_by_email(db, email=user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )
        
    user = crud.app_user.update(db, db_obj=current_user, obj_in=user_in)
    return user




@router.get("/me", response_model=schemas.AppUserPublic)
def read_user_me(current_user: models.AppUser = Depends(deps.get_current_active_user)) -> Any:
    """
    Get current user.
    """
    print(current_user,"this is current user") 
    return current_user

