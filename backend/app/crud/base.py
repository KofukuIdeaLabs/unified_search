from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session
import datetime
from app.db.base_class import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).

        **Parameters**

        * `model`: A SQLAlchemy model class
        * `schema`: A Pydantic model (schema) class
        """
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        if hasattr(self.model, "deleted_at"):
            return (
                db.query(self.model)
                .filter(self.model.id == id, self.model.deleted_at == None)
                .first()
            )
        return db.query(self.model).filter(self.model.id == id).first()

    def get_all(
        self,
        db: Session,
    ) -> List[ModelType]:
        if hasattr(self.model, "deleted_at"):
            return db.query(self.model).filter(self.model.deleted_at == None)
        
        return db.query(self.model).all()


    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        if hasattr(self.model, "deleted_at"):
            return (
                db.query(self.model)
                .filter(self.model.deleted_at == None)
                .all()
            )
        return db.query(self.model).offset(skip).limit(limit).all()

    def get_by_column_one(self, db: Session, filter_column, filter_value):
        filter_column = getattr(self.model, filter_column)
        if hasattr(self.model, "deleted_at"):
            return (
                db.query(self.model)
                .filter(filter_column == filter_value, self.model.deleted_at == None)
                .one_or_none()
            )
        return db.query(self.model).filter(filter_column == filter_value).first()

    def get_by_column_first(self, db: Session, filter_column, filter_value):
        filter_column = getattr(self.model, filter_column)
        if hasattr(self.model, "deleted_at"):
            return (
                db.query(self.model)
                .filter(filter_column == filter_value, self.model.deleted_at == None)
                .first()
            )
        return db.query(self.model).filter(filter_column == filter_value).first()

    def get_by_column_latest_created(self, db: Session, filter_column, filter_value):
        filter_column = getattr(self.model, filter_column)
        if hasattr(self.model, "deleted_at"):
            return (
                db.query(self.model)
                .filter(filter_column == filter_value, self.model.deleted_at == None)
                .order_by(self.model.created_at.desc())
                .first()
            )
        return (
            db.query(self.model)
            .filter(filter_column == filter_value)
            .order_by(self.model.created_at.desc())
            .first()
        )

    def get_by_column_many(
        self, db: Session, filter_column, filter_value, limit: int = 100
    ):
        filter_column = getattr(self.model, filter_column)
        if hasattr(self.model, "deleted_at"):
            return (
                db.query(self.model)
                .filter(filter_column.in_(filter_value), self.model.deleted_at == None)
                .limit(100)
                .all()
            )
        return db.query(self.model).filter(filter_column == filter_value).all()

    def get_by_column_all(
        self, db: Session, filter_column, filter_value, limit: int = 100
    ) -> List[ModelType]:
        filter_column = getattr(self.model, filter_column)
        if hasattr(self.model, "deleted_at"):
            return (
                db.query(self.model)
                .filter(filter_column.in_(filter_value), self.model.deleted_at == None)
                .all()
            )
        return db.query(self.model).filter(filter_column == filter_value).all()

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)  # type: ignore
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
    ) -> ModelType:
        obj_data = jsonable_encoder(db_obj)
        obj_in_data = jsonable_encoder(obj_in)
        for field in obj_data:
            if (field in obj_in_data) and obj_in_data[field] is not None:
                setattr(db_obj, field, obj_in_data[field])
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, db_obj: ModelType) -> ModelType:
        if hasattr(self.model, "deleted_at"):
            db_obj.deleted_at = datetime.datetime.utcnow()
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        db.delete(db_obj)
        db.commit()
        return db_obj
    
    def bulk_insert(self, db: Session, data_in) -> List[ModelType]:
        db_objs = [self.model(**jsonable_encoder(obj_data)) for obj_data in data_in]
        db.add_all(db_objs)
        db.flush()
        db.commit()
        # Refresh each object individually
        for obj in db_objs:
            db.refresh(obj)

        return db_objs

