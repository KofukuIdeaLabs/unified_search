from typing import Optional,List

from app.crud.base import CRUDBase
from app.models.form_instance import FormInstance
from app.schemas.form_instance import FormInstanceCreate, FormInstanceUpdate
from sqlalchemy.orm import Session
from pydantic import UUID4


class CRUDFormInstance(CRUDBase[FormInstance, FormInstanceCreate, FormInstanceUpdate]):
    pass


form_instance = CRUDFormInstance(FormInstance)
