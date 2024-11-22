import uuid
from typing import Any, List
from pydantic.types import UUID4
from fastapi import APIRouter, Depends, HTTPException
from app import crud,schemas,models
from sqlalchemy.orm import Session
from app.api import deps
from app.core.config import settings
import csv
from app.core.security import get_password_hash, verify_password

router = APIRouter()


@router.get("/all", response_model=List[schemas.IndexedTable])
def get_indexed_tables(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.AppUser = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve all indexed tables.
    """
    indexed_tables = crud.indexed_table.get_multi(db, skip=skip, limit=limit)
    return indexed_tables


@router.post(
    "/", dependencies=[Depends(deps.get_current_active_superuser)], response_model=schemas.IndexedTable
)
def create_indexed_table(*, db: Session = Depends(deps.get_db), indexed_table_in: schemas.IndexedTableCreate) -> Any:
    """
    Create new user.
    """
    indexed_table = crud.indexed_table.get_by_column_first(db, filter_column="name", filter_value=indexed_table_in.name)
    if indexed_table:
        raise HTTPException(
            status_code=400,
            detail="The indexed table with this name already exists in the system.",
        )

    indexed_table = crud.indexed_table.create(db, obj_in=indexed_table_in)
    return indexed_table


@router.put("/{indexed_table_id}", response_model=schemas.IndexedTable)
def update_indexed_table(indexed_table_id: UUID4, indexed_table_in: schemas.IndexedTableUpdate,
    db: Session = Depends(deps.get_db), current_user: models.AppUser = Depends(deps.get_current_active_superuser)) -> Any:
    """
    Update a indexed table.
    """
    indexed_table = crud.indexed_table.get(db, indexed_table_id)
    if not indexed_table:
        raise HTTPException(status_code=404, detail="Indexed table not found")
    indexed_table = crud.indexed_table.update(db, indexed_table_id, obj_in=indexed_table_in)
    return indexed_table


@router.delete("/{indexed_table_id}"   )
def delete_indexed_table(indexed_table_id: UUID4,
    db: Session = Depends(deps.get_db), current_user: models.AppUser = Depends(deps.get_current_active_superuser)) -> Any:
    """
    Delete a indexed table.
    """
    indexed_table = crud.indexed_table.get(db, indexed_table_id)
    if not indexed_table:
        raise HTTPException(status_code=404, detail="Indexed table not found")
    indexed_table = crud.indexed_table.remove(db, indexed_table_id)
    return indexed_table


@router.post("/data")
def add_from_file(db: Session = Depends(deps.get_db), current_user: models.AppUser = Depends(deps.get_current_active_superuser)):
    with open("app/files/tables.csv",mode='r') as csvfile:
        csv_reader = csv.DictReader(csvfile)
        for row in csv_reader:
            print(row.get("id"),"this is id")
            print(row.get("table"),"this is table")
            indexed_table_in = schemas.IndexedTableCreate(id=row.get("id"),name=row.get("table"),db_id="d377ec7d-804f-4ba9-a3c8-245fdf37400e",description="string")
            try:
                indexed_table = crud.indexed_table.create(db, obj_in=indexed_table_in)
            except Exception as e:
                pass
            print(indexed_table)    
