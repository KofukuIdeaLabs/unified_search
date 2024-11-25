from typing import Optional

from app.crud.base import CRUDBase
from app.models.indexed_table_column import IndexedTableColumn
from app.schemas.indexed_table_column import IndexedTableColumnCreate, IndexedTableColumnUpdate
from sqlalchemy.orm import Session
from pydantic import UUID4

class CRUDIndexedTableColumn(CRUDBase[IndexedTableColumn, IndexedTableColumnCreate, IndexedTableColumnUpdate]):
   def get_column_by_name_and_table_id(self,db:Session,name:str,table_id:UUID4):
      return db.query(IndexedTableColumn).filter(IndexedTableColumn.name==name,IndexedTableColumn.table_id==table_id).first()
   
   def get_columns_by_table_id(self,db:Session,table_id:UUID4):
      return db.query(IndexedTableColumn.name,IndexedTableColumn.unique_values,IndexedTableColumn.id).filter(IndexedTableColumn.table_id==table_id).all()

indexed_table_column = CRUDIndexedTableColumn(IndexedTableColumn)
