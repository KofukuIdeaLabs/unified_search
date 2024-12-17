from collections.abc import Generator
from typing import Annotated, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.db.session import SessionLocal
from app.schemas import TokenPayload,Token,AppUserPublic
from app import crud
from app.models import AppUser
from app.constants.role import Role
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login"
)

optional_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login",
    auto_error=False
)

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()






def get_current_user( db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)) -> AppUser:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = crud.app_user.get_with_roles(db, id=token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user



CurrentUser = Annotated[AppUser, Depends(get_current_user)]

def get_current_active_user(current_user: CurrentUser) -> AppUser:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


CurrentActiveUser = Annotated[AppUser, Depends(get_current_active_user)]


def get_current_active_superuser(current_user: CurrentActiveUser) -> AppUser:
    if not current_user.role_name == Role.SUPER_ADMIN["name"]:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user

CurrentActiveSuperuser = Annotated[AppUser,Depends(get_current_active_superuser)]

async def get_current_user_or_guest(
    db: Session = Depends(get_db), 
    token: Optional[str] = Depends(optional_oauth2)
) -> Optional[AppUser]:
    """
    Similar to get_current_user but returns guest user if no token or invalid token is provided.
    Returns the authenticated user if valid token is provided.
    """
    if not token:
        # Return guest user when no token is provided
        return crud.app_user.get_guest_user(db)
        
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        # Return guest user when token is invalid
        return crud.app_user.get_guest_user(db)
        
    user = crud.app_user.get_with_roles(db, id=token_data.sub)
    if not user or not user.is_active:
        # Return guest user when user is not found or inactive
        return crud.app_user.get_guest_user(db)
        
    return user

CurrentUserOrGuest = Annotated[Optional[AppUserPublic], Depends(get_current_user_or_guest)]

async def get_current_active_user_or_guest_active(
    current_user_or_guest: CurrentUserOrGuest
) -> Optional[AppUser]:
    """
    Similar to get_current_active_user but returns None if user is not active
    instead of raising an exception
    """
    if not current_user_or_guest.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user_or_guest


# Create type annotations for easier usage
CurrentActiveUserOrGuest = Annotated[AppUserPublic, Depends(get_current_active_user_or_guest_active)]
