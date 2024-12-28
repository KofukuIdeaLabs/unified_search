import uuid
from typing import Any, List
from pydantic.types import UUID4
from fastapi import APIRouter, Depends, HTTPException
from app import crud,schemas,models
from sqlalchemy.orm import Session
from app.api import deps
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.api.deps import CurrentActiveUserOrGuest

router = APIRouter()


@router.get("/", response_model=List[schemas.IndexedDB])
def get_indexed_dbs(
   current_user_or_guest: CurrentActiveUserOrGuest,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve all indexed dbs.
    """
    indexed_dbs = crud.indexed_db.get_multi(db, skip=skip, limit=limit)
    return indexed_dbs


@router.post(
    "/", dependencies=[Depends(deps.get_current_active_superuser)], response_model=schemas.IndexedDB
)
def create_indexed_db(*, db: Session = Depends(deps.get_db), indexed_db_in: schemas.IndexedDBCreate) -> Any:
    """
    Create new user.
    """
    indexed_db = crud.indexed_db.get_by_column_first(db, filter_column="name", filter_value=indexed_db_in.name)
    if indexed_db:
        raise HTTPException(
            status_code=400,
            detail="The indexed db with this name already exists in the system.",
        )

    indexed_db = crud.indexed_db.create(db, obj_in=indexed_db_in)
    return indexed_db


@router.put("/{indexed_db_id}", response_model=schemas.IndexedDB)
def update_indexed_db(indexed_db_id: UUID4, indexed_db_in: schemas.IndexedDBUpdate,
    db: Session = Depends(deps.get_db), current_user: models.AppUser = Depends(deps.get_current_active_superuser)) -> Any:
    """
    Update a indexed db.
    """
    indexed_db = crud.indexed_db.get(db, indexed_db_id)
    if not indexed_db:
        raise HTTPException(status_code=404, detail="Indexed db not found")
    indexed_db = crud.indexed_db.update(db, indexed_db_id, obj_in=indexed_db_in)
    return indexed_db


@router.delete("/{indexed_db_id}"   )
def delete_indexed_db(indexed_db_id: UUID4,
    db: Session = Depends(deps.get_db), current_user: models.AppUser = Depends(deps.get_current_active_superuser)) -> Any:
    """
    Delete a indexed db.
    """
    indexed_db = crud.indexed_db.get(db, indexed_db_id)
    if not indexed_db:
        raise HTTPException(status_code=404, detail="Indexed db not found")
    indexed_db = crud.indexed_db.remove(db, indexed_db_id)
    return indexed_db
