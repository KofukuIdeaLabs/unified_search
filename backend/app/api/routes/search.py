import uuid
from typing import Any, List
from app import schemas,crud,models,constants
from fastapi import APIRouter, Depends, HTTPException
from app import crud,schemas,models
from sqlalchemy.orm import Session
from app.api import deps


router = APIRouter()


@router.post("/term", response_model=schemas.SearchResult)
def create_search_term(
    search_in: schemas.SearchCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.AppUser = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create a search.
    """
    print(current_user.id,"this is the user id")
    search_in.search_type = constants.SearchType.TERM
    search_in.model_dump().update({"user_id": current_user.id})
    search = crud.search.create(db, obj_in=search_in)
    table_names = search_in.input_search.table_names  
    search_term = search_in.input_search.search_text    
    meiliresults = crud.meilisearch.search(index_name=table_names[0],search_query=search_term)
    print(meiliresults,"these are meilieresuts")
    search_result_in = schemas.SearchResultCreate(search_id=search.id,result=[{"table_name":table_names[0],"result_data":meiliresults}])
    search_result = crud.search_result.create(db=db,obj_in=search_result_in)
    return search_result


@router.post("/query", response_model=schemas.SearchId)
def create_search_query(
    search_in:schemas.SearchCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.AppUser = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create a search.
    """
    search = crud.search.create(db, obj_in=search_in)
    return search


@router.post(
    "/", dependencies=[Depends(deps.get_current_active_superuser)], response_model=schemas.AppUser
)
def create_user(*, db: Session = Depends(deps.get_db), user_in: schemas.AppUserCreate) -> Any:
    """
    Create new user.
    """
    user = crud.app_user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    user = crud.app_user.create(db, obj_in=user_in)
    return user


@router.patch("/me", response_model=schemas.AppUser)
def update_user_me(
    *, db: Session = Depends(deps.get_db), user_in: schemas.AppUserUpdate, current_user: deps.CurrentActiveUser
) -> Any:
    """
    Update own user.
    """

    if user_in.email:
        existing_user = crud.app_user.get_by_email(db, email=user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )
        
    user = crud.app_user.update(db, db_obj=current_user, obj_in=user_in)
    return user


# @router.patch("/me/password", response_model=Message)
# def update_password_me(
#     *, session: SessionDep, body: UpdatePassword, current_user: CurrentUser
# ) -> Any:
#     """
#     Update own password.
#     """
#     if not verify_password(body.current_password, current_user.hashed_password):
#         raise HTTPException(status_code=400, detail="Incorrect password")
#     if body.current_password == body.new_password:
#         raise HTTPException(
#             status_code=400, detail="New password cannot be the same as the current one"
#         )
#     hashed_password = get_password_hash(body.new_password)
#     current_user.hashed_password = hashed_password
#     session.add(current_user)
#     session.commit()
#     return Message(message="Password updated successfully")


# @router.get("/me", response_model=UserPublic)
# def read_user_me(current_user: CurrentUser) -> Any:
#     """
#     Get current user.
#     """
#     return current_user


# @router.delete("/me", response_model=Message)
# def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
#     """
#     Delete own user.
#     """
#     if current_user.is_superuser:
#         raise HTTPException(
#             status_code=403, detail="Super users are not allowed to delete themselves"
#         )
#     statement = delete(Item).where(col(Item.owner_id) == current_user.id)
#     session.exec(statement)  # type: ignore
#     session.delete(current_user)
#     session.commit()
#     return Message(message="User deleted successfully")


# @router.post("/signup", response_model=UserPublic)
# def register_user(session: SessionDep, user_in: UserRegister) -> Any:
#     """
#     Create new user without the need to be logged in.
#     """
#     user = crud.get_user_by_email(session=session, email=user_in.email)
#     if user:
#         raise HTTPException(
#             status_code=400,
#             detail="The user with this email already exists in the system",
#         )
#     user_create = UserCreate.model_validate(user_in)
#     user = crud.create_user(session=session, user_create=user_create)
#     return user


# @router.get("/{user_id}", response_model=UserPublic)
# def read_user_by_id(
#     user_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
# ) -> Any:
#     """
#     Get a specific user by id.
#     """
#     user = session.get(User, user_id)
#     if user == current_user:
#         return user
#     if not current_user.is_superuser:
#         raise HTTPException(
#             status_code=403,
#             detail="The user doesn't have enough privileges",
#         )
#     return user


# @router.patch(
#     "/{user_id}",
#     dependencies=[Depends(get_current_active_superuser)],
#     response_model=UserPublic,
# )
# def update_user(
#     *,
#     session: SessionDep,
#     user_id: uuid.UUID,
#     user_in: UserUpdate,
# ) -> Any:
#     """
#     Update a user.
#     """

#     db_user = session.get(User, user_id)
#     if not db_user:
#         raise HTTPException(
#             status_code=404,
#             detail="The user with this id does not exist in the system",
#         )
#     if user_in.email:
#         existing_user = crud.get_user_by_email(session=session, email=user_in.email)
#         if existing_user and existing_user.id != user_id:
#             raise HTTPException(
#                 status_code=409, detail="User with this email already exists"
#             )

#     db_user = crud.update_user(session=session, db_user=db_user, user_in=user_in)
#     return db_user


# @router.delete("/{user_id}", dependencies=[Depends(get_current_active_superuser)])
# def delete_user(
#     session: SessionDep, current_user: CurrentUser, user_id: uuid.UUID
# ) -> Message:
#     """
#     Delete a user.
#     """
#     user = session.get(User, user_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     if user == current_user:
#         raise HTTPException(
#             status_code=403, detail="Super users are not allowed to delete themselves"
#         )
#     statement = delete(Item).where(col(Item.owner_id) == user_id)
#     session.exec(statement)  # type: ignore
#     session.delete(user)
#     session.commit()
#     return Message(message="User deleted successfully")
