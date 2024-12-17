import uuid
from typing import Any, List
from pydantic.types import UUID4
from fastapi import APIRouter, Depends, HTTPException
from app import crud,schemas,models
from sqlalchemy.orm import Session
from app.api import deps
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.api.deps import CurrentActiveUser

router = APIRouter()



@router.get("/", response_model=List[schemas.FormInstance])
def get_form_instances(
    current_user: CurrentActiveUser,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    get form instance
    """
    form_instances = crud.form_instance.get_multi(db=db,skip=skip,limit=limit)
    return form_instances


@router.get("/template/{form_template_id}", response_model=schemas.FormInstance)
def get_form_instance_by_template_id(
    current_user: CurrentActiveUser,
    form_template_id:int,
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    get form instance by template id
    """
    form_template = crud.form_template.get_by_column_first(db=db,filter_column="id",filter_value=form_template_id)
    if not form_template:
        raise HTTPException(status_code=404,detail="Form Template Doesn't Exists.")
    form_instance = crud.form_instance.get_by_column_first(db=db,filter_column="template_id",filter_value=form_template.id)
    if not form_instance:
        raise HTTPException(status_code=404,detail="Form Instance Doesn't Exists.")
    return form_instance


@router.get("/{form_instance_id}", response_model=schemas.FormInstance)
def get_form_instance_by_id(
    form_instance_id:int,
    current_user: CurrentActiveUser,
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    get form instance by template id
    """
    form_instance = crud.form_instance.get_by_column_first(db=db,filter_column="id",filter_value=form_instance_id)
    if not form_instance:
        raise HTTPException(status_code=404,detail="Form Instance Doesn't Exists.")
    return form_instance



@router.put("/{form_instance_id}", response_model=schemas.FormInstance)
def update_form_instance(
    current_user: CurrentActiveUser,
    form_instance_id:int,
    form_instance_update_in:schemas.FormInstanceUpdate,
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    Update a form Instance.
    """
    form_instance = crud.form_instance.get(db=db,id=form_instance_id)
    if not form_instance:
        raise HTTPException(status_code=404,detail="Form Instance not found")
    form_instance = crud.form_instance.update(db=db,db_obj=form_instance,obj_in=form_instance_update_in)
    return form_instance


@router.delete("/{form_instance_id}", response_model=schemas.FormInstance)
def delete_form_instance(
    current_user: CurrentActiveUser,
    form_instance_id:int,
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    Delete a form instance.
    """
    form_instance = crud.form_instance.get(db=db,id=form_instance_id)
    if not form_instance:
        raise HTTPException(status_code=404,detail="Form Instance not found")
    form_instance = crud.form_instance.remove(db=db,db_obj=form_instance)
    return form_instance
