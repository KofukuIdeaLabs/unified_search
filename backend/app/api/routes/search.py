import uuid
from typing import Any, List
from app import schemas,crud,models,constants
from fastapi import APIRouter, Depends, HTTPException
from app import crud,schemas,models
from sqlalchemy.orm import Session
from app.api import deps
from app.core.config import settings
import requests
from app.celery_app.tasks import process_term_search
from celery.result import AsyncResult
from app.celery_app.celery import app
from fastapi.responses import StreamingResponse
import pandas as pd
import io
from app.api.deps import CurrentActiveUserOrGuest
import time

router = APIRouter()


@router.post("/term", response_model=schemas.SearchId)
def create_search_term(
    current_user_or_guest: CurrentActiveUserOrGuest,
    search_in: schemas.SearchCreate,
    db: Session = Depends(deps.get_db),
    skip:int = 0,
    limit:int = 20,
) -> Any:
    """
    Create a search and queue it for async processing.
    """
    # Set up the search record
    search_in.search_type = constants.SearchType.TERM
    search_data = search_in.model_dump()
    search_data["user_id"] = current_user_or_guest.id
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
        current_user_or_guest.role_id,
        str(search.id),
        search_in.input_search.search_text,
        search_in.input_search.table_ids if search_in.input_search.table_ids else None,
        exact_match,
        0,
        60
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



# @router.get("/download/result/{search_id}")
# def download_result(
#     current_user_or_guest: CurrentActiveUserOrGuest,
#     search_id: uuid.UUID,
#     table_id: uuid.UUID | None = None,
#     db: Session = Depends(deps.get_db),
 
# ):
#     search_result = crud.search_result.get_by_column_first(db=db,filter_column="search_id",filter_value=search_id)
#     if not search_result:
#         raise HTTPException(status_code=404,detail="Search result not found")

#     # Create an in-memory buffer
#     output = io.BytesIO()
    
#     # Write DataFrame(s) to Excel file in memory
#     with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
#         if table_id:
#             # get table name
#             table = crud.indexed_table.get(db=db,id=table_id)
#             if not table:
#                 raise HTTPException(status_code=404,detail="Table not found")
#             table_name = table.name 
#             display_name = table.display_name
#             # Find the matching result for the requested table_name
#             table_result = None
#             for result in search_result.result:
#                 print(result,"these are results")
#                 print(str(table_id),"this is table id",str(result["table_id"]))
#                 if str(result["table_id"]) == str(table_id):
#                     table_result = result["result_data"]
#                     break
                    
#             if table_result is None:
#                 raise HTTPException(status_code=404,detail="Table not found in search result")
            
#             # Convert table_result to pandas DataFrame and write to Excel
#             df = pd.DataFrame(table_result)
#             df.to_excel(writer, sheet_name=display_name, index=False)
#             filename = f"{display_name}.xlsx"
#         else:
#             # Write all tables as separate sheets
#             for result in search_result.result:
#                 table_name = result["table_name"]
#                 table_data = result["result_data"]
#                 df = pd.DataFrame(table_data)
#                 df.to_excel(writer, sheet_name=table_name[:31], index=False)
#             filename = "search_results.xlsx"
    
#     # Seek to start of buffer
#     output.seek(0)
    
#     # Return the Excel file as a streaming response
#     headers = {
#         'Content-Disposition': f'attachment; filename="{filename}"'
#     }
#     return StreamingResponse(
#         output,
#         media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
#         headers=headers
#     )


@router.get("/download/result/{search_id}")
def download_result(
    current_user_or_guest: CurrentActiveUserOrGuest,
    search_id: uuid.UUID,
    table_id: uuid.UUID | None = None,
    db: Session = Depends(deps.get_db),
):
    # Retrieve the search object
    search = crud.search.get(db=db, id=search_id)
    if not search:
        raise HTTPException(status_code=404, detail="Search not found")

    # Trigger a Celery task for processing the search
    task = process_term_search.apply_async(args=[
        current_user_or_guest.role_id,
        str(search.id),
        search.input_search["search_text"],
        [table_id] if table_id else search.input_search["table_ids"],
        search.input_search["exact_match"],
        0,
        1000
    ])

    return {"task_id":task.id}

    


@router.get("/download/task")
def download_result(
    current_user_or_guest: CurrentActiveUserOrGuest,
    search_id: uuid.UUID,
    task_id:str,
    db: Session = Depends(deps.get_db),
):

    task_status = _check_task_status([task_id])
    if task_status == "success":

        # Fetch the search result after task completion
        search_result = crud.search_result.get_by_column_first(
            db=db, filter_column="search_id", filter_value=search_id
        )
        if not search_result:
            raise HTTPException(status_code=404, detail="Search result not found")

        # Prepare an in-memory buffer for Excel data
        output = io.BytesIO()

        # Write DataFrame(s) to Excel file in memory
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                # Write all tables as separate sheets
                for result in search_result.result:
                    table_name = result["table_name"]
                    table_data = result["result_data"]
                    df = pd.DataFrame(table_data)
                    df.to_excel(writer, sheet_name=table_name[:31], index=False)
                filename = "search_results.xlsx"

        # Seek to the start of the buffer
        output.seek(0)

        # Return the Excel file as a streaming response
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers
        )
    else:
        return {"status":task_status}



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
    current_user_or_guest: CurrentActiveUserOrGuest,
    search_id: uuid.UUID,
    db: Session = Depends(deps.get_db)
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


@router.get("/result/{search_id}/{table_id}", response_model=schemas.SearchResult)
def get_search_result_by_table_id(
    current_user_or_guest: CurrentActiveUserOrGuest,
    search_id: uuid.UUID,
    table_id: str,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(deps.get_db)
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


    # Find the specific table's data
    table_result = next(
        (result for result in (search_result.result or []) if result.get("table_name") == table_name),
        None
    )

    # print(len(table_result.get("result_data")),"len of table result is this")

    
    # needs_new_search = True
    # if table_result:
    #     # Get pagination info from the table's data
    #     table_pagination = table_result.get("pagination", {})

    #     current_max_offset = table_pagination.get("skip", 0) + table_pagination.get("limit", 0)

        
    #     # If requesting data within our current range
    #     if skip + limit <= current_max_offset:
    #         needs_new_search = False
  
            
    #         # Update only this table's data with pagination
    #         table_result["result_data"] = table_result["result_data"][skip:skip + limit]
    #         table_result["pagination"] = {
    #             "skip": skip,
    #             "limit": limit,
    #         }
    
    #         search_result.status = "success"
    #         search_result.result = [table_result]

    if table_result:
        # Get the total data length
        result_data_length = len(table_result.get("result_data", []))

        # If skip is greater than or equal to the data length, return empty
        if skip >= result_data_length:
            table_result["result_data"] = []
            table_result["pagination"] = {
                "skip": skip,
                "limit": limit,
            }
            search_result.status = "success"
            search_result.result = [table_result]
        else:
            # Calculate the end index, ensuring it doesn't exceed the data length
            end_index = min(skip + limit, result_data_length)

            # Slice the data from skip to end_index
            table_result["result_data"] = table_result["result_data"][skip:end_index]

            # Add pagination details
            table_result["pagination"] = {
                "skip": skip,
                "limit": limit,
            }

            # Set the result
            search_result.status = "success"
            search_result.result = [table_result]


    
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
    current_user_or_guest: CurrentActiveUserOrGuest,
    search_text:str,
    db:Session = Depends(deps.get_db),
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