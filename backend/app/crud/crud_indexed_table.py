from typing import Optional,List

from app.crud.base import CRUDBase
from app.models.indexed_table import IndexedTable
from app.schemas.indexed_table import IndexedTableCreate, IndexedTableUpdate
from sqlalchemy.orm import Session


class CRUDIndexedTable(CRUDBase[IndexedTable, IndexedTableCreate, IndexedTableUpdate]):
    def get_table_by_name_and_db_id(self,db:Session,name:str,db_id:int):
        return db.query(IndexedTable).filter(IndexedTable.name==name,IndexedTable.db_id==db_id).first()
    def get_tables_by_ids(self,db:Session,table_ids:List[str]):
        return db.query(IndexedTable).filter(IndexedTable.id.in_(table_ids)).all()


indexed_table = CRUDIndexedTable(IndexedTable)
