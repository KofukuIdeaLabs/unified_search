import uuid
from typing import Any, List
from app import schemas,crud,models,constants
from fastapi import APIRouter, Depends, HTTPException
from app import crud,schemas,models
from sqlalchemy.orm import Session
from app.api import deps
from app.core.config import settings
import requests
from app.celery_app.tasks import run_sql_query,process_term_search
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
    skip:int = 0,
    limit:int = 20,
    current_user: models.AppUser = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create a search and queue it for async processing.
    """
    # Set up the search record
    search_in.search_type = constants.SearchType.TERM
    search_data = search_in.model_dump()
    search_data["user_id"] = current_user.id
    exact_match = search_in.input_search.exact_match
    optimize_search = search_in.input_search.optimize_search
    search_in = schemas.SearchCreate(**search_data)
    search = crud.search.create(db, obj_in=search_in)
    
    # Create initial search result with pending status
    search_result_in = schemas.SearchResultCreate(
        search_id=search.id
    )
    search_result = crud.search_result.create(db=db, obj_in=search_result_in)
    
    # Queue the search task with exact_match parameter and initial pagination
    task = process_term_search.apply_async(args=[
        str(search.id),
        search_in.input_search.search_text,
        search_in.input_search.table_ids if search_in.input_search.table_ids else None,
        exact_match,
        skip,
        limit
    ])
    
    # Update search result with task ID
    crud.search_result.update(
        db=db,
        db_obj=search_result,
        obj_in=schemas.SearchResultUpdate(
            extras={
                "task_id": task.id,
            }
        )
    )
    
    return {"id": search.id}


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


def _get_and_validate_search(db: Session, search_id: uuid.UUID):
    """Get and validate search exists"""
    search = crud.search.get(db=db, id=search_id)
    if not search:
        raise HTTPException(status_code=404, detail="Search not found")
    return search

def _get_and_validate_search_result(db: Session, search_id: uuid.UUID):
    """Get and validate search result exists"""
    search_result = crud.search_result.get_by_column_first(
        db=db,
        filter_column="search_id", 
        filter_value=search_id
    )
    if not search_result:
        raise HTTPException(status_code=404, detail="Search result not found")
    return search_result

def _handle_term_search(search_result):
    """Handle term-based search results"""
    task_id = search_result.extras.get("task_id", [])

    search_result.status = _check_task_status([task_id])
    return search_result

def _process_sql_queries(db: Session, search_result, external_search_id):
    """Process SQL queries and create tasks"""
    url = f"{settings.BACKEND_BASE_URL}/api/v1/db_scaled/search/{external_search_id}"
    
    try:
        response = requests.get(url, headers={'accept': 'application/json'})
        response.raise_for_status()
        sql_queries = response.json()

        if sql_queries:
            # Start async tasks
            test_queries = [{"sql_query":["select * from indexed_db","select * from appuser"]}]
            test_queries = test_queries[0]["sql_query"]
            
            try:
                sql_queries = sql_queries.get("sql_query")
            except:
                sql_queries = None

            # Create tasks for each query
            task_ids = [
                run_sql_query.apply_async(args=[search_result.id, [query]]).id 
                for query in test_queries
            ]
            
            # Update search result
            updated_extras = {
                "sql_queries": sql_queries,
                "external_search_id": external_search_id,
                "task_ids": task_ids
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
    
    return search_result

def _check_task_status(task_ids):
    """Check status of all tasks and determine overall status"""
    all_completed = True
    any_failed = False
    
    for task_id in task_ids:
        result = AsyncResult(task_id, app=app)
        if result.state.lower() not in ["success", "failed"]:
            all_completed = False
        if result.state.lower() == "failed":
            any_failed = True
    
    if any_failed:
        return "failed"
    elif all_completed:
        return "success"
    return "pending"

@router.get("/result/{search_id}", response_model=schemas.SearchResult)
def get_search_result(
    search_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_user: models.AppUser = Depends(deps.get_current_active_user),
):
    """Get search results for a given search ID"""
    # Get and validate search and search result
    search = _get_and_validate_search(db, search_id)
    search_result = _get_and_validate_search_result(db, search_id)
    
    # Add search text to result
    search_result.search_text = search.input_search["search_text"]
    
    # Handle term-based searches
    if search.search_type == constants.SearchType.TERM:
        return _handle_term_search(search_result)

    # Handle query searches
    extras = search_result.extras or {}
    external_search_id = extras.get("external_search_id")
    if not external_search_id:
        raise HTTPException(status_code=400, detail="External search ID not found")

    sql_queries = extras.get("sql_queries")
    task_ids = extras.get("task_ids", [])

    # Process queries if needed
    if not sql_queries or not task_ids:
        search_result = _process_sql_queries(db, search_result, external_search_id)
    # Check task status if tasks exist
    elif task_ids:
        search_result.status = _check_task_status(task_ids)

    return search_result


@router.get("/result/{search_id}/{table_id}", response_model=schemas.SearchResult)
def get_search_result(
    search_id: uuid.UUID,
    table_id: str,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(deps.get_db),
    current_user: models.AppUser = Depends(deps.get_current_active_user),
):
    """Get search results for a given search ID and table name"""
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

    table = crud.indexed_table.get(db=db,id=table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    table_name = table.name

    print(table_name,"this is the table_name")

    # Find the specific table's data
    table_result = next(
        (result for result in (search_result.result or []) if result.get("table_name") == table_name),
        None
    )

    print(table_result,"this is the table result")
    
    needs_new_search = True
    if table_result:
        # Get pagination info from the table's data
        table_pagination = table_result.get("pagination", {})
        print(table_pagination,"this is the table pagination")
        current_max_offset = table_pagination.get("skip", 0) + table_pagination.get("limit", 0)
        print(current_max_offset,"this is the current max offset")
        
        # If requesting data within our current range
        if skip + limit <= current_max_offset:
            needs_new_search = False
            print("Using cached data")
            
            # Update only this table's data with pagination
            table_result["result_data"] = table_result["result_data"][skip:skip + limit]
            table_result["pagination"] = {
                "skip": skip,
                "limit": limit,
            }
            print(table_result,"this is the table result after pagination")
            search_result.status = "success"
            search_result.result = [table_result]

    if needs_new_search:
        print("Triggering new search")
        # Need to fetch new data
        task = process_term_search.apply_async(args=[
            str(search.id),
            search.input_search["search_text"],
            [table_id],  # Only search the specific table
            search.input_search.get("exact_match", False),
            skip,
            limit
        ])
        
        # Update search result with new task ID
        crud.search_result.update(
            db=db,
            db_obj=search_result,
            obj_in=schemas.SearchResultUpdate(
                status="pending",
                extras={
                    **search_result.extras,
                    "task_id": task.id
                }
            )
        )
        search_result.result = []
        search_result.status = "pending"
    
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


# Add a new endpoint to check task status
@router.get("/task/{task_id}")
def get_task_status(
    task_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.AppUser = Depends(deps.get_current_active_user),
):
    """Check the status of a search task"""
    result = AsyncResult(task_id, app=app)
    return {
        "status": result.state.lower(),
        "ready": result.ready()
    }