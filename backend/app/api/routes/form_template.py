from uuid import uuid4
from typing import Any, List
from pydantic.types import UUID4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.sql.functions import current_user
from app import crud,schemas,models
from sqlalchemy.orm import Session
from app.api import deps
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.api.deps import CurrentActiveUser,CurrentActiveSuperuser
from app.constants.form_template_element import FormTemplateElement
import copy
from app.utils import create_or_update_form_instance,delete_form_instance,assign_uuids_to_template


router = APIRouter()





@router.get("/", response_model=List[schemas.FormTemplate])
def get_all_form_templates(
    current_user: CurrentActiveSuperuser,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve all form templates.
    """
    form_templates = crud.form_template.get_multi(db, skip=skip, limit=limit)
    return form_templates





@router.post("/", response_model=schemas.FormTemplate)
def create_form_template(    
    current_user: CurrentActiveSuperuser,
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    Create a new form template.
    """
    # Fetch the field from form_template_elements
    form_template_element = crud.form_template_element.get_by_column_first(
        db=db,
        filter_column="name",
        filter_value=FormTemplateElement.FIELD_GROUP["name"]
    )
    
    # Deep copy the template to avoid in-memory modifications
    template = copy.deepcopy(form_template_element.template)

    # Assign UUIDs to the copied template
    assign_uuids_to_template(template)
    
    # Create a new form template in the database
    form_template_in = schemas.FormTemplateCreate(
        template=[template],
        owner_id=current_user.id,
        organization_id=current_user.org_id
    )
    form_template = crud.form_template.create(db=db, obj_in=form_template_in)
    create_or_update_form_instance(db=db,form_template=form_template)
    return form_template

@router.get(
    "/{form_template_id}", response_model=schemas.FormTemplate
)
def get_form_template(    
    current_user: CurrentActiveSuperuser,
    form_template_id:int,
    db: Session = Depends(deps.get_db),
    ) -> Any:
    """
    get a form template by id
    """
    form_template = crud.form_template.get_by_column_first(db=db,filter_column="id",filter_value=form_template_id)
    if not form_template:
        raise HTTPException(status_code=404,detail="Form Template Doesn't Exists.")
    return form_template


@router.post(
    "/{form_template_id}/field", response_model=schemas.FormTemplate
)
def add_field_to_form_template(    
    current_user: CurrentActiveSuperuser,
    form_template_id:int,
    db: Session = Depends(deps.get_db),
    ) -> Any:
    """
    add a field to the form template.
    """
    # right now this only add one type of field because we are only using that but we can extend it to use more field types
    # check if form_template exists
    form_template = crud.form_template.get_by_column_first(db=db,filter_column="id",filter_value=form_template_id)
    if not form_template:
        raise HTTPException(status_code=404,detail="Form Template Doesn't Exists.")
    # fetch the field from form_template_elements
    form_template_element = crud.form_template_element.get_by_column_first(db=db,filter_column="name",filter_value=FormTemplateElement.FIELD_GROUP["name"])
    # here add id to the uuid to the filed
    form_template_element_data = form_template_element.template
    assign_uuids_to_template(form_template_element_data)
    print(form_template.template,"this is before")
    print(form_template_element_data,"this is the data")
    form_template.template.append(form_template_element_data)
    print(form_template.template,"this is after")

    form_template_in = schemas.FormTemplateUpdate(template=form_template.template)
    form_template = crud.form_template.update(db=db,db_obj=form_template,obj_in=form_template_in)
    create_or_update_form_instance(db=db,form_template=form_template)
    return form_template



@router.put("/{form_template_id}", response_model=schemas.FormTemplate)
def update_form_template(
    current_user: CurrentActiveSuperuser,
    form_template_id:int,
    form_template_update_in:schemas.FormTemplateUpdate,
    db: Session = Depends(deps.get_db)
    ) -> Any:
    """
    Update a Form Template
    """
    # get form template by id
    form_template = crud.form_template.get_by_column_first(db=db,filter_column="id",filter_value=form_template_id)
    if not form_template:
        raise HTTPException(status_code=404,detail="Form Template Doesn't Exists.")
    form_template = crud.form_template.update(db=db,db_obj=form_template, obj_in=form_template_update_in)
    create_or_update_form_instance(db=db,form_template=form_template)
    return form_template


@router.delete("/{form_template_id}",response_model=schemas.FormTemplate)
def delete_form_template(
    current_user: CurrentActiveSuperuser,
    form_template_id:int,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Delete a Form Template.
    """
    form_template = crud.form_template.get_by_column_first(db=db,filter_column="id",filter_value=form_template_id)
    if not form_template:
        raise HTTPException(status_code=404,detail="Form Template Doesn't Exists.")
    form_template = crud.form_template.remove(db, db_obj=form_template)
    # delete form instance
    delete_form_instance(db,form_template_id=form_template.id)
    return form_template


@router.get("/{form_template_id}/field/{field_id}/attribute/{attribute_name}/options",response_model=schemas.FormTemplateFieldOptions)
def get_dynamic_options_for_the_field(
    current_user: CurrentActiveSuperuser,
    form_template_id:int,
    attribute_name:str,
    field_id:UUID4,
    db: Session = Depends(deps.get_db)
) -> Any:
    # get the form_template
    form_template = crud.form_template.get_by_column_first(db=db,filter_column="id",filter_value=form_template_id)
    if not form_template:
        raise HTTPException(status_code=404,detail="Form Template Doesn't Exists.")

    options = []
    # get the field
    template = form_template.template
    # extract the field from the template
    target_field = next((field for field in template if field.get("id") == str(field_id)), None)

    if not target_field:
        raise HTTPException(status_code=404, detail="Field Not Found.")


    if attribute_name == "field_type" :
        options = [{"label":"Text","value":"text_input"},{"label":"Textarea","value":"text_area"}]
        # Optimize search for 'Display Label' in elements
    elif attribute_name == "value_type":
        field_type = next(
            (attr for attributes in target_field.get("elements", []) for attr in attributes
             if attr.get("name") == "field_type"),
            None
        )
        if field_type:
            print(field_type,"this is the field type")
            if isinstance(field_type.get("value"), dict) and field_type["value"].get("value") == "text_input":

                options = [{"label":"Number","value":"number"},{"label":"String","value":"string"}]
            elif isinstance(field_type.get("value"), dict) and field_type["value"].get("value") == "text_area":
                options = [{"label":"String","value":"string"}]
    elif attribute_name == "aliases":
        display_label = next(
            (attr for attributes in target_field.get("elements", []) for attr in attributes
             if attr.get("name") == "display_label"),
            None
        )
        if display_label:
            print(display_label,"this is the display label")
            options = [{"label":"Father Name","value":"f_name"},{"label":"Mother Name","value":"m_name"}]
    return {"options":options}
   



