from typing import Optional,List

from app.crud.base import CRUDBase
from app.models.form_template import FormTemplate
from app.schemas.form_template import FormTemplateCreate, FormTemplateUpdate
from sqlalchemy.orm import Session
from pydantic import UUID4


class CRUDFormTemplate(CRUDBase[FormTemplate, FormTemplateCreate, FormTemplateUpdate]):
    pass


form_template = CRUDFormTemplate(FormTemplate)
