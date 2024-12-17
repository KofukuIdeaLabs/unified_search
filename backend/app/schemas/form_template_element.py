from typing import Optional

from pydantic import UUID4, BaseModel
from datetime import datetime


# Shared properties
class FormTemplateElementBase(BaseModel):
    name: Optional[str] = None
    template: Optional[dict] = None


# Properties to receive via API on creation
class FormTemplateElementCreate(FormTemplateElementBase):
    name: str
    template: dict


# Properties to receive via API on update
class FormTemplateElementUpdate(FormTemplateElementBase):
    pass


class FormTemplateElementInDBBase(FormTemplateElementBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# Additional properties to return via API
class FormTemplateElement(FormTemplateElementInDBBase):
    pass


class FormTemplateElementInDB(FormTemplateElementInDBBase):
    pass

