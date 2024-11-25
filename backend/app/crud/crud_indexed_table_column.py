from typing import Optional

from app.crud.base import CRUDBase
from app.models.indexed_table_column import IndexedTableColumn
from app.schemas.indexed_table_column import IndexedTableColumnCreate, IndexedTableColumnUpdate
from sqlalchemy.orm import Session


class CRUDIndexedTableColumn(CRUDBase[IndexedTableColumn, IndexedTableColumnCreate, IndexedTableColumnUpdate]):
   pass

indexed_table_column = CRUDIndexedTableColumn(IndexedTableColumn)
