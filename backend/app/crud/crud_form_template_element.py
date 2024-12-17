from typing import Optional,List

from app.crud.base import CRUDBase
from app.models.form_template_element import FormTemplateElement
from app.schemas.form_template_element import FormTemplateElementCreate, FormTemplateElementUpdate
from sqlalchemy.orm import Session
from pydantic import UUID4


class CRUDFormTemplateElement(CRUDBase[FormTemplateElement, FormTemplateElementCreate, FormTemplateElementUpdate]):
    pass


form_template_element = CRUDFormTemplateElement(FormTemplateElement)
