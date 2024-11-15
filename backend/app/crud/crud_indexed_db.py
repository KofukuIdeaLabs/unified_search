from typing import Optional

from app.crud.base import CRUDBase
from app.models.indexed_db import IndexedDB
from app.schemas.indexed_db import IndexedDBCreate, IndexedDBUpdate
from sqlalchemy.orm import Session


class CRUDIndexedDB(CRUDBase[IndexedDB, IndexedDBCreate, IndexedDBUpdate]):
    pass


indexed_db = CRUDIndexedDB(IndexedDB)
