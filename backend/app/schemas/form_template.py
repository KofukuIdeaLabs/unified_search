from typing import Optional

from pydantic import UUID4, BaseModel
from datetime import datetime


# Shared properties
class FormTemplateBase(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    template: Optional[list] = None
    organization_id: Optional[UUID4] = None
    owner_id: Optional[UUID4] = None
    extras : Optional[dict] = None


# Properties to receive via API on creation
class FormTemplateCreate(FormTemplateBase):
    template: list


# Properties to receive via API on update
class FormTemplateUpdate(FormTemplateBase):
    pass


class FormTemplateInDBBase(FormTemplateBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# Additional properties to return via API
class FormTemplate(FormTemplateInDBBase):
    pass


class FormTemplateInDB(FormTemplateInDBBase):
    pass


class FormTemplateFieldOptions(BaseModel):
    options:list

