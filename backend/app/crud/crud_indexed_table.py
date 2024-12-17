from typing import Optional,List

from app.crud.base import CRUDBase
from app.models.indexed_table import IndexedTable
from app.schemas.indexed_table import IndexedTableCreate, IndexedTableUpdate
from sqlalchemy.orm import Session
from pydantic import UUID4


class CRUDIndexedTable(CRUDBase[IndexedTable, IndexedTableCreate, IndexedTableUpdate]):
    def get_table_by_name_and_db_id(self,db:Session,name:str,db_id:int):
        return db.query(IndexedTable).filter(IndexedTable.name==name,IndexedTable.db_id==db_id).first()
    def get_tables_by_ids(self,db:Session,table_ids:List[str]):
        return db.query(IndexedTable).filter(IndexedTable.id.in_(table_ids)).all()
    def get_all_tables(self,db:Session):
        return db.query(IndexedTable).all()

    def get_tables_by_role(self, db: Session, role_id: UUID4):
        return (
            db.query(IndexedTable)
            .filter(
                # Return all tables if access_to_roles is None/empty, otherwise check for role_id
                (
                    (IndexedTable.access_to_roles == None) |  # noqa
                    (IndexedTable.access_to_roles == []) |
                    IndexedTable.access_to_roles.contains([role_id])
                ),
                IndexedTable.deleted_at.is_(None)  # Only get non-deleted tables
            )
            .all()
        )


indexed_table = CRUDIndexedTable(IndexedTable)
