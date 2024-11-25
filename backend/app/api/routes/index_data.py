import uuid
from typing import Any, List,Optional
from pydantic.types import UUID4
from fastapi import APIRouter, Depends, HTTPException,UploadFile,File
from app import crud,schemas,models
from sqlalchemy.orm import Session
from app.api import deps
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.celery_app.tasks import index_data_file
from pathlib import Path

router = APIRouter()


@router.post("/index_data/file")
async def index_data(
   db_id: Optional[UUID4] = None,
   db_name: Optional[str] = None,
   files: List[UploadFile] = File(...),
   db: Session = Depends(deps.get_db)
) -> Any:
    """
    Process file data for indexing.
    
    Args:
        db_id: Optional UUID of the indexed database
        db_name: Optional name for new database if db_id is not provided
        files: List of files to process
        db: Database session
    """
    if not db_id and not db_name:
        raise HTTPException(
            status_code=400,
            detail="Either db_id or db_name must be provided"
        )

        
    if not db_id:
        #create a new indexed db
        indexed_db_in = schemas.IndexedDBCreate(name=db_name, description=db_name)
        indexed_db = crud.indexed_db.create(db, obj_in=indexed_db_in)
        db_id = indexed_db.id
    else:
        indexed_db = crud.indexed_db.get(db, db_id)
        if not indexed_db:
            raise HTTPException(status_code=404, detail="Indexed db not found")
    
    # Create temp directory if it doesn't exist
    base_upload_dir = Path("/storage")
    upload_dir = base_upload_dir.joinpath(str(uuid.uuid4()))

    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Save files and collect paths
    saved_files = []
    try:
        for file in files:
            file_path = upload_dir.joinpath(Path(file.filename).name)
            try:
                with file_path.open("wb") as f:
                    content = await file.read()
                    f.write(content)
                saved_files.append({
                    "filename": file.filename,
                    "path": str(file_path),
                    "content_type": file.content_type
                })
            finally:
                await file.close()
        print(saved_files,"this is the saved files")
        
        task = index_data_file.apply_async(args=[str(db_id), saved_files])
        return {"task_id": task.id}
    
    except Exception as e:
        if upload_dir.exists():
            import shutil
            shutil.rmtree(upload_dir)
        raise HTTPException(status_code=500, detail=str(e))

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
