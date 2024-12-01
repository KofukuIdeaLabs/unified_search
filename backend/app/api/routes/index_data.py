import uuid
from typing import Any, List,Optional
from pydantic.types import UUID4
from fastapi import APIRouter, Depends, HTTPException,UploadFile,File
from app import crud,schemas,models
from sqlalchemy.orm import Session
from app.api import deps
from app.core.config import settings
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
    base_upload_dir = Path(settings.UPLOAD_DIR)
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



@router.post("/index_data/file_local")
async def index_data_local(
    index_data_in: schemas.IndexDataLocal,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Process file data for indexing from a local folder.
    
    Args:
        db_id: Optional UUID of the indexed database
        db_name: Optional name for new database if db_id is not provided
        folder_path: Path to the local folder containing files to process
        db: Database session
    """

    indexed_db = crud.indexed_db.get_by_column_first(db, filter_column="name", filter_value=index_data_in.db_name)
    if not indexed_db:  
        #create a new indexed db
        indexed_db_in = schemas.IndexedDBCreate(name=index_data_in.db_name, description=index_data_in.db_name)
        indexed_db = crud.indexed_db.create(db, obj_in=indexed_db_in)
    
    folder_path = Path(index_data_in.folder_path)
    if not folder_path.exists() or not folder_path.is_dir():
        raise HTTPException(status_code=400, detail="Invalid folder path")

    # Collect files from the local folder
    saved_files = []
    try:
        for file_path in folder_path.rglob('*'):
            if file_path.is_file():
                extension = file_path.suffix.lower()
                
                # Only process CSV and Excel files
                if extension in ['.csv']:
                    content_type = 'text/csv'
                elif extension in ['.xlsx', '.xls']:
                    content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                else:
                    continue  # Skip files that aren't CSV or Excel
                
                saved_files.append({
                    "filename": file_path.name,
                    "path": str(file_path),
                    "content_type": content_type
                })
        
        if not saved_files:
            raise HTTPException(
                status_code=400,
                detail="No CSV or Excel files found in the specified folder"
            )
            
        task = index_data_file.apply_async(args=[str(indexed_db.id), saved_files])
        return {"task_id": task.id}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))