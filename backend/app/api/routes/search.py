import uuid
from typing import Any, List
from app import schemas,crud,models,constants
from fastapi import APIRouter, Depends, HTTPException
from app import crud,schemas,models
from sqlalchemy.orm import Session
from app.api import deps
from app.core.config import settings
import requests
from app.celery_app.tasks import run_sql_query
from celery.result import AsyncResult
from app.celery_app.celery import app
from fastapi.responses import StreamingResponse
import pandas as pd
import io

router = APIRouter()


@router.post("/term", response_model=schemas.SearchId)
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
    table_ids = search_in.input_search.table_ids  
    search_term = search_in.input_search.search_text    
    meiliresults = crud.meilisearch.search(index_name="kp_employee",search_query=search_term)
    print(meiliresults,"these are meilieresuts")
    search_result_in = schemas.SearchResultCreate(search_id=search.id,result=[{"table_name":"kp_employee","result_data":meiliresults},{"table_name":"kp_employee","result_data":meiliresults},{"table_name":"kp_employee","result_data":meiliresults},{"table_name":"kp_employee","result_data":meiliresults},{"table_name":"kp_employee","result_data":meiliresults},{"table_name":"kp_employee","result_data":meiliresults},{"table_name":"kp_employee","result_data":meiliresults},{"table_name":"kp_employee","result_data":meiliresults},{"table_name":"kp_employee","result_data":meiliresults},{"table_name":"kp_employee","result_data":meiliresults},{"table_name":"kp_employee","result_data":meiliresults},{"table_name":"kp_employee","result_data":meiliresults},{"table_name":"kp_employee","result_data":meiliresults},{"table_name":"kp_employee","result_data":meiliresults},{"table_name":"kp_employee","result_data":meiliresults}])
    search_result = crud.search_result.create(db=db,obj_in=search_result_in)
    search_result.search_text = search_term
    return {"id":search.id}


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
        data["input_search"]["db_id"] = str(search_in.input_search.db_id)
        data["input_search"]["table_ids"] = [str(table_id) for table_id in search_in.input_search.table_ids]
        print(data,"this is the data")
        response = requests.post(url, json=data)
        response.raise_for_status()  # Raises an HTTPError for bad status codes
        print(response.json(),"this is the response")
        search_result_in = schemas.SearchResultCreate(search_id=search.id,extras={"external_search_id":response.json()})
        search_result = crud.search_result.create(db=db,obj_in=search_result_in)
        print(search_result.id,"this is the search result")
    except requests.exceptions.RequestException as e:
        print(f'An error occurred: {e}')

    return {"id":search.id}


@router.post("/generate/user_query",response_model=schemas.GenerateUserQueryOutput)
def query_on_data(
    query_on_data_in: schemas.GenerateUserQueryInput,
    db: Session = Depends(deps.get_db),
    current_user: models.AppUser = Depends(deps.get_current_active_user),
):
    try:
        data = query_on_data_in.model_dump()
        print(data,"this is the data")
        url = "{0}/api/v1/db_scaled/generate/user_query".format(settings.BACKEND_BASE_URL)
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }

        response = requests.post(url, headers=headers, json=data)

        print(response.json(),"this is the response")
        result = response.json()
        return {"query":result.get("content")}
    except requests.exceptions.RequestException as e:
        print(f'An error occurred: {e}')
        raise HTTPException(status_code=400, detail=f"Failed to generate SQL queries: {str(e)}")
@router.get("/download/result/{search_id}")
def download_result(
    search_id: uuid.UUID,
    table_name: str | None = None,
    db: Session = Depends(deps.get_db),
    current_user: models.AppUser = Depends(deps.get_current_active_user),
):
    search_result = crud.search_result.get_by_column_first(db=db,filter_column="search_id",filter_value=search_id)
    if not search_result:
        raise HTTPException(status_code=404,detail="Search result not found")

    # Create an in-memory buffer
    output = io.BytesIO()
    
    # Write DataFrame(s) to Excel file in memory
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        if table_name:
            # Find the matching result for the requested table_name
            table_result = None
            for result in search_result.result:
                if result["table_name"] == table_name:
                    table_result = result["result_data"]
                    break
                    
            if table_result is None:
                raise HTTPException(status_code=404,detail="Table not found in search result")
            
            # Convert table_result to pandas DataFrame and write to Excel
            df = pd.DataFrame(table_result)
            df.to_excel(writer, sheet_name=table_name, index=False)
            filename = f"{table_name}.xlsx"
        else:
            # Write all tables as separate sheets
            for result in search_result.result:
                table_name = result["table_name"]
                table_data = result["result_data"]
                df = pd.DataFrame(table_data)
                df.to_excel(writer, sheet_name=table_name, index=False)
            filename = "search_results.xlsx"
    
    # Seek to start of buffer
    output.seek(0)
    
    # Return the Excel file as a streaming response
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"'
    }
    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers=headers
    )




@router.get("/result/{search_id}",response_model=schemas.SearchResult)
def get_search_result(
    search_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_user: models.AppUser = Depends(deps.get_current_active_user),
):
    """Get search results for a given search ID"""
    # Get search and validate it exists
    search = crud.search.get(db=db, id=search_id)
    if not search:
        raise HTTPException(status_code=404, detail="Search not found")

    # Get search result and validate it exists
    search_result = crud.search_result.get_by_column_first(
        db=db,
        filter_column="search_id", 
        filter_value=search_id
    )
    if not search_result:
        raise HTTPException(status_code=404, detail="Search result not found")
    
    search_result.search_text = search.input_search["search_text"]

    # Return immediately for term searches
    if search.search_type == constants.SearchType.TERM:
        search_result.status = "success"
        return search_result

    # Handle query searches
    extras = search_result.extras or {}
    external_search_id = extras.get("external_search_id")
    if not external_search_id:
        raise HTTPException(
            status_code=400, 
            detail="External search ID not found"
        )

    sql_queries = extras.get("sql_queries")
    task_id = extras.get("task_id")
    print(task_id,"this is the task id")

    # If no existing queries/task, fetch and start task
    if not sql_queries or not task_id:
        url = f"{settings.BACKEND_BASE_URL}/api/v1/db_scaled/search/{external_search_id}"
        
        try:
            response = requests.get(url, headers={'accept': 'application/json'})
            response.raise_for_status()
            sql_queries = response.json()
            print(sql_queries,"this is the sql queries")

            if sql_queries:
                # Start async task
                test_queries = [{"sql_query":["select * from indexed_db","select * from appuser"]}]
                test_queries = test_queries[0]["sql_query"]
                try:
                    sql_queries = sql_queries.get("sql_query")
                except:
                    sql_queries = None
                task = run_sql_query.apply_async(args=[search_result.id, test_queries])
                
                # Update search result with new data
                updated_extras = {
                    "sql_queries": sql_queries,
                    "external_search_id": external_search_id,
                    "task_id": task.id
                }
                search_result = crud.search_result.update(
                    db=db,
                    db_obj=search_result,
                    obj_in=schemas.SearchResultUpdate(extras=updated_extras)
                )
                search_result.status = "pending"

        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to generate SQL queries: {str(e)}"
            )

    # Check task status if task exists
    elif task_id:
        result = AsyncResult(task_id,app=app)
        search_result.status = result.state.lower()

    return search_result

    


    





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
    results = crud.meilisearch.search_autocomplete(
        search_query=search_text,
        index_name="kp_employee"
    )
    if len(results) > 0:
        return extract_matched_values(results)
    else:
        return []  # Raise exception


