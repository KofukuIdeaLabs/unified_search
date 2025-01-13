import uuid
from typing import Any, List
from collections import defaultdict

from kombu.exceptions import HttpError
from pandas._libs import index
from app import schemas,crud,models,constants
from fastapi import APIRouter, Depends, HTTPException
from app import crud,schemas,models
from sqlalchemy.orm import QueryEvents, Session
from app.api import deps
from app.core.config import settings
import requests
from app.celery_app.tasks import run_sql_query,process_term_search,execute_meilisearch_query
from celery.result import AsyncResult
from app.celery_app.celery import app
from fastapi.responses import StreamingResponse
import pandas as pd
import io
from app.api.deps import CurrentActiveUserOrGuest
from app.utils import parse_form_instance_data
from app.constants import QueryType,SearchType


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
        search_in.input_search.query,
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



    try:

        data = search_in.model_dump()
        data.pop('search_type', None)
        print(data,"this is the data")

        # instance id
        parsed_form_data = None
        form_instance_id = None
        form_data = []
        for item in data["input_search"]["query"]:
            if item.get("type") == "form_data":
                form_instance_id = item.get("form_instance_id")
                form_data.append(item)
        print(form_instance_id,"form instance id")
        print(form_data,"form data")
        if form_instance_id:
            # fetch the form_instance
            form_instance = crud.form_instance.get_by_column_first(db=db,filter_column="id",filter_value=form_instance_id)
            if not form_instance:
                raise HTTPException(status_code=404,detail="form instance not found")
            # process data fetch template
            form_template = crud.form_template.get_by_column_first(db=db,filter_column="id",filter_value=form_instance.template_id)
            if not form_template:
                raise HTTPException(status_code=404,detail="form_template not found")
            parsed_form_data = parse_form_instance_data(form_instance_data=form_data,form_template_data=form_template.template)
            # "give me details of people whose phone number ends with 01"
        table_ids = search_in.input_search.table_ids
        table_dict = defaultdict(list)
        # fetch the index names for meiliesearch
        if table_ids:
            # tables = crud.indexed_table.get_tables_by_ids(db=db, table_ids=table_ids)
            table_columns = crud.indexed_table_column.get_by_table_ids(db=db,table_ids=table_ids)
            print(table_columns,"this is the table columns")
            for column_name, table_name in table_columns:
                table_dict[table_name].append(column_name)
        else:
            # tables = crud.indexed_table.get_tables_by_role(db=db,role_id=current_user.role_id)
            table_columns = crud.indexed_table_column.get_column_names(db=db)
            print(table_columns,"these are table_columns")
            for column_name, table_name in table_columns:
                table_dict[table_name].append(column_name)


        index_names = [{"table_name": table, "columns": columns} for table, columns in table_dict.items()]
        print(index_names,"this is the index name")


        data["input"] = {"db_id": str(search_in.input_search.db_id),"table_ids":[str(table_id) for table_id in search_in.input_search.table_ids],"query" :search_in.input_search.query,"form_data":parsed_form_data,"index_names":index_names}
        data["name"] = "search"
        data.pop("input_search",None)
        print(data,"this is the data")
        print("Data to be send to crawlermlservice", data)
        response = requests.post(url, json=data)
        response.raise_for_status()  # Raises an HTTPError for bad status codes
        search_result_in = schemas.SearchResultCreate(search_id=search.id,extras={"external_search_id":response.json()})
        search_result = crud.search_result.create(db=db,obj_in=search_result_in)
    except requests.exceptions.RequestException as e:
        print(f'An error occurred: {e}')

    return {"id":search.id}

def transform_data_to_stringified_output(input_data):
    """
    Transforms a list of input dictionaries into a structured output.
    Non-None values from dictionaries are concatenated into a string, and None values are removed.

    Parameters:
        input_data (list): A list of dictionaries or strings.

    Returns:
        list: A structured list with `type` and concatenated stringified `data`.
    """
    if not input_data:
        return []

    result = []

    # Add an initial descriptive string
    result.append({"type": "string", "data": "Provide information about the following items"})  # Dynamic string possible

    # Process each item in the input data
    for obj in input_data:
        if isinstance(obj, dict):
            # Filter out None values and join the remaining values as a string
            stringified_data = ",".join(str(value) for value in obj.values() if value is not None)
            result.append({"type": "dict", "data": stringified_data})
        elif isinstance(obj, list):  # Handle lists if needed
            stringified_data = ",".join(str(item) for item in obj if item is not None)
            result.append({"type": "dict", "data": stringified_data})

    return result

# @router.post("/generate/user_query",response_model=schemas.GeneratePromptOutputResponse
# )
# def query_on_data(
#     query_on_data_in: schemas.GenerateUserQueryInput,
#     db: Session = Depends(deps.get_db),
#     current_user: models.AppUser = Depends(deps.get_current_active_user),
# ):
#     try:
#         result = transform_data_to_stringified_output(query_on_data_in.data)
#         return {"result":result}
        
#     #     data = query_on_data_in.model_dump()
#     #     url = "{0}/api/v1/db_scaled/generate/user_query".format(settings.BACKEND_BASE_URL)
#     #     headers = {
#     #         "accept": "application/json",
#     #         "Content-Type": "application/json"
#     #     }

#     #     response = requests.post(url, headers=headers, json=data)

#     #     result = response.json()
#     #     return {"query":result.get("content")}
#     except requests.exceptions.RequestException as e:
#         print(f'An error occurred: {e}')
#         raise HTTPException(status_code=400, detail=f"Failed to generate SQL queries: {str(e)}")
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

    if search.search_type == SearchType.TERM:
        task = process_term_search.apply_async(args=[
        current_user_or_guest.role_id,
        str(search.id),
        search.input_search["query"],
        [table_id] if table_id else search.input_search["table_ids"],
        search.input_search["exact_match"],
        0,
        1000
    ])
        task_id = task.id
    
    else:
        #TODO: handle query download
        task_id = search.id

    # Trigger a Celery task for processing the search
    

    return {"task_id":task_id}

    


@router.get("/download/task")
def download_task(
    current_user_or_guest: CurrentActiveUserOrGuest,
    search_id: uuid.UUID,
    task_id:str,
    db: Session = Depends(deps.get_db),
):

    search = crud.search.get(db=db,id=search_id)
    print(search.id,"this is the search id")
    print(task_id,"this is the task id")
    if not search:
        raise HTTPException(status_code=404, detail="Search not found")
    if task_id == str(search.id): #it means i am return existing results for query
        search_result = crud.search_result.get_by_column_first(
                db=db, filter_column="search_id", filter_value=search_id
            )
        if not search_result:
            raise HTTPException(status_code=404, detail="Search result not found")

        print(search_result.result,"this is the search result")

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

        task_status = _check_task_status([task_id])
        if task_status == "success":

            # Fetch the search result after task completion
            search_result = crud.search_result.get_by_column_first(
                db=db, filter_column="search_id", filter_value=search_id
            )
            if not search_result:
                raise HTTPException(status_code=404, detail="Search result not found")

            print(search_result.result,"this is the search result")

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


def _process_sql_queries(db: Session, role_id,search_id,search_query, external_search_id,table_ids,skip,limit):
    """Process SQL queries and create tasks"""
    url = f"{settings.BACKEND_BASE_URL}/api/v1/db_scaled/search/{external_search_id}"
    
    try:
        response = requests.get(url, headers={'accept': 'application/json'})
        response.raise_for_status()
        query_response = response.json()
        print(query_response,"this is the sql queries")
        search_result = crud.search_result.get_by_column_first(db=db,filter_column="search_id",filter_value=search_id)

        if query_response:
            # Start async tasks
            # test_queries = [{"sql_query":["select * from indexed_db","select * from app_user"]}]
            # test_queries = test_queries[0]["sql_query"]
            query_type = query_response.get("query_type")
            queries = query_response.get("queries",[])
            # queries = [{'indexUid': 'name_age_rank', 'q': '', 'attributesToSearchOn': ['*'], 'limit': 50, 'offset': 0, 'filter': "Name = 'eve' AND Name = 'eve' AND Age = '59' AND Age = '59' AND Rank = '51'"}]

            print(query_type,"query type")
            print(queries,"queries")


            if query_type == QueryType.MEILISEARCH:
                
                # We are only limited to kp_employee so we will only be including kp_employee index
                # Will be removed in production

                # if queries:
                #     # insert kp_employee for testing
                #     kp_employee_query = queries[0]
                #     kp_employee_query["indexUid"] = "kp_employee"
                #     queries = [kp_employee_query]
                
                task_ids = [execute_meilisearch_query.apply_async(args=[role_id,search_id,search_query,queries,table_ids,skip,limit]).id]
            else:

                # Create tasks for each query
                task_ids = [
                    run_sql_query.apply_async(args=[search_id, [query]]).id 
                    for query in test_queries
                ]

            
            
            
            # Update search result
            updated_extras = {
                "queries": queries,
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

@router.get("/result/{search_id}", response_model=schemas.SearchResult
)
def get_search_result(
    current_user_or_guest: CurrentActiveUserOrGuest,
    search_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    skip:int = 0,
    limit:int = 20,
):
    """Get search results for a given search ID"""
    # Get and validate search and search result
    search = _get_and_validate_search(db, search_id)
    print(search.input_search.get("table_ids"),"this is the input search")
    table_ids = search.input_search.get("table_ids")
    search_result = _get_and_validate_search_result(db, search_id)

    query = search.input_search["query"]
    
    # Add search text to result
    search_result.search_text = query
    
    # Handle term-based searches
    if search.search_type == constants.SearchType.TERM:
        return _handle_term_search(search_result)

    # Handle query searches
    extras = search_result.extras or {}
    external_search_id = extras.get("external_search_id") #api service
    if not external_search_id:
        raise HTTPException(status_code=400, detail="External search ID not found")

    queries = extras.get("queries")
    print(queries,"this is the sql queries")
    task_ids = extras.get("task_ids", [])

    # Process queries if needed
    if not queries or not task_ids:
        search_result = _process_sql_queries(db, current_user_or_guest.role_id ,search_id,query ,external_search_id,table_ids,skip,limit)
    # Check task status if tasks exist
    elif task_ids:
        print("tasks ids are there",task_ids)
        search_result.status = _check_task_status(task_ids)

    return search_result


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
    extras = search_result.extras or {}
    external_search_id = extras.get("external_search_id")


    query = search.input_search["query"]
    
    search_result.search_text = query

    table = crud.indexed_table.get(db=db,id=table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    table_name = table.name


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

        current_max_offset = table_pagination.get("skip", 0) + table_pagination.get("limit", 0)

        
        # If requesting data within our current range
        if skip + limit <= current_max_offset:
            needs_new_search = False
  
            
            # Update only this table's data with pagination
            table_result["result_data"] = table_result["result_data"][skip:skip + limit]
            table_result["pagination"] = {
                "skip": skip,
                "limit": limit,
            }
    
            search_result.status = "success"
            search_result.result = [table_result]

    if needs_new_search:

        if search.search_type == SearchType.TERM:
 
            # Need to fetch new data
            task = process_term_search.apply_async(args=[
                current_user_or_guest.role_id,
                str(search.id),
                search.input_search["query"],
                [table_id],  # Only search the specific table
                search.input_search.get("exact_match", False),
                skip,
                limit
            ])
        elif search.search_type == SearchType.QUERY:
            _process_sql_queries(db,current_user_or_guest.role_id,search_id=search_id,search_query=query,external_search_id=external_search_id,table_ids=[table_id],skip=skip,limit=limit)
        
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
    current_user_or_guest: CurrentActiveUserOrGuest,
    search_text:str,
    db:Session = Depends(deps.get_db),
):
    results = crud.meilisearch.search_autocomplete(
        search_query=search_text,
        index_name=None # "kp_employee"
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