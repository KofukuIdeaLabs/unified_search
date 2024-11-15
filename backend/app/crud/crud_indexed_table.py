from typing import Optional

from app.crud.base import CRUDBase
from app.models.indexed_table import IndexedTable
from app.schemas.indexed_table import IndexedTableCreate, IndexedTableUpdate
from sqlalchemy.orm import Session


class CRUDIndexedTable(CRUDBase[IndexedTable, IndexedTableCreate, IndexedTableUpdate]):
    pass


indexed_table = CRUDIndexedTable(IndexedTable)
