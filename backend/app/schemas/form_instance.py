from typing import Optional

from pydantic import UUID4, BaseModel
from datetime import datetime


# Shared properties
class FormInstanceBase(BaseModel):
    name: Optional[str] = None
    form: Optional[list] = None
    responses: Optional[dict] = None
    owner_id: Optional[UUID4] = None
    template_id: Optional[int] = None


# Properties to receive via API on creation
class FormInstanceCreate(FormInstanceBase):
    form: list
    owner_id: UUID4
    template_id: int
    


# Properties to receive via API on update
class FormInstanceUpdate(FormInstanceBase):
    pass


class FormInstanceInDBBase(FormInstanceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# Additional properties to return via API
class FormInstance(FormInstanceInDBBase):
    pass


class FormInstanceInDB(FormInstanceInDBBase):
    pass



