import uuid
from typing import Any, List
from app import schemas,crud,models,constants
from fastapi import APIRouter, Depends, HTTPException
from app import crud,schemas,models
from sqlalchemy.orm import Session
from app.api import deps
from app.core.config import settings
import requests
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
    search_data = search_in.model_dump()
    search_data["user_id"] = current_user.id
    search_in = schemas.SearchCreate(**search_data)
    print(search_in.model_dump(),"this is the search in")
    search = crud.search.create(db, obj_in=search_in)
    tables_data = search_in.input_search.table_data  
    search_term = search_in.input_search.search_text    
    meiliresults = crud.meilisearch.search(index_name="kp_employee",search_query=search_term)
    print(meiliresults,"these are meilieresuts")
    search_result_in = schemas.SearchResultCreate(search_id=search.id,result=[{"table_name":"kp_employee","result_data":meiliresults}])
    search_result = crud.search_result.create(db=db,obj_in=search_result_in)
    search_result.search_text = search_term
    return search_result


@router.post("/query", response_model=schemas.SearchId
             )
def create_search_query(
    search_in:schemas.SearchCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.AppUser = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create a search.
    """

    search = crud.search.create(db, obj_in=search_in)

    url = "{0}/api/v1/db_scaled/generate_query".format(settings.BACKEND_BASE_URL)

    print(url,"this is the url")


    try:

        data = search_in.model_dump()
        data.pop('search_type', None)
        response = requests.post(url, json=data)
        response.raise_for_status()  # Raises an HTTPError for bad status codes
        print(response.json(),"this is the response")
        search_result_in = schemas.SearchResultCreate(search_id=search.id,extras={"external_search_id":response.json()})
        search_result = crud.search_result.create(db=db,obj_in=search_result_in)
        print(search_result.id,"this is the search result")
    except requests.exceptions.RequestException as e:
        print(f'An error occurred: {e}')

    return {"id":search.id}

@router.get("/result/{search_id}",response_model=schemas.SearchResult)
def get_search_result(
    search_id:uuid.UUID,
    db:Session = Depends(deps.get_db)
):
    
    search_result = crud.search_result.get_by_column_first(db=db,filter_column="search_id",filter_value=search_id)
    return search_result


# @router.get("/result/{search_result_id}",response_model=schemas.SearchResult)
# def get_search_result(
#     search_result_id:uuid.UUID,
#     db:Session = Depends(deps.get_db)
# ):
#     search_result = crud.search_result.get(db=db,id=search_result_id)
#     return search_result


def extract_matched_values(data):
    # List to store matched values
    matched_values = []

    # Loop through each dictionary in the data
    for entry in data:
        # Check if '_matchesPosition' key exists
        if '_matchesPosition' in entry:
            for column, positions in entry['_matchesPosition'].items():
                # If the column is in the dictionary, extract its value
                if column in entry:
                    value = entry.get(column)
                    if value not in matched_values:
                        matched_values.append(value)
    
    return matched_values

@router.get("/recent",response_model=List[schemas.RecentSearch]
            )
def get_recent_searches(
    db:Session = Depends(deps.get_db),
    current_user: models.AppUser = Depends(deps.get_current_active_user)
):
    return crud.search.get_recent_searches(db=db,user_id=current_user.id)


@router.get("/autocomplete")
def get_autocomplete(
    search_text:str,
    db:Session = Depends(deps.get_db),
    current_user: models.AppUser = Depends(deps.get_current_active_user)
):
    results = crud.meilisearch.search(
        search_query=search_text,
        index_name="kp_employee"
    )
    if len(results) > 0:
        return extract_matched_values(results)
    else:
        return []  # Raise exception
