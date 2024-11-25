from .celery import app
from app.api import deps
import time
from app import crud, schemas,models
import sqlparse
from sqlparse.sql import Identifier, IdentifierList
from sqlparse.tokens import Keyword, DML
from sqlalchemy import text
from pathlib import Path
from typing import List
import uuid
import pandas as pd
import numpy as np
from app.utils.excel_parser import excel_file_parser
import re
import json
import requests
import os
from app.utils.index_data import index_data

def extract_table_names(sql_query):
    """
    Extracts the first table name from a SQL query using sqlparse.
    Handles case-insensitive 'FROM' keyword.
    """
    parsed = sqlparse.parse(sql_query)
    
    for statement in parsed:
        from_seen = False  # To track when we encounter the FROM keyword

        for token in statement.tokens:
            if from_seen:
                # Handle single table name
                if isinstance(token, Identifier):
                    return token.get_real_name()
                # Handle multiple table names (comma-separated) - take first one
                elif isinstance(token, IdentifierList):
                    for identifier in token.get_identifiers():
                        return identifier.get_real_name()
            elif token.ttype is Keyword and token.value.upper() == "FROM":
                from_seen = True  # FROM keyword encountered

    # Fallback for very simple queries (case-insensitive)
    tokens = sql_query.split()
    lower_tokens = [token.lower() for token in tokens]
    if "from" in lower_tokens:
        index = lower_tokens.index("from")
        if index + 1 < len(tokens):
            return tokens[index + 1]  # Return first table after FROM

    return None


@app.task(bind=True)
def run_sql_query(self, search_result_id, query):
    try:
        db = next(deps.get_db())
        if not query or not isinstance(query, list):
            raise ValueError("Query must be a non-empty list")
            
        sql = query[0]
        print(f"Task {search_result_id}: Running query: {sql}")
        
        # Execute query and get results
        query_result = [dict(row._mapping) for row in db.execute(text(sql)).fetchall()]
        result = {
            "table_name": extract_table_names(sql),
            "result_data": query_result
        }
        
        # Get current results and append new result
        search_result = crud.search_result.get(db=db, id=search_result_id)
        current_results = search_result.result or []
        current_results.append(result)
        
        # Update search result with combined results
        search_result_update_in = schemas.SearchResultUpdate(result=current_results)
        search_result = crud.search_result.update(
            db=db,
            db_obj=search_result,
            obj_in=search_result_update_in
        )
        
        return True
    except Exception as e:
        print(f"Error executing query: {str(e)}")
        raise self.retry(exc=e)

@app.task(bind=True, max_retries=3)
def index_data_file(self, db_id: str, saved_files: List[dict]):
    # i need to index in melisearch as it is for search
    # as well as i need to generate table synonyms, column synonyms, table descriptions and column descriptions
    # need to index table name, column name, column synonym, column description, table synonym, table description into meilisearch and vdb
    try:
        db = next(deps.get_db())
        for file_info in saved_files:
            file_path = Path(file_info["path"])
            content_type = file_info["content_type"]
            filename = file_info["filename"]
            
            try:
                # Handle different content types appropriately
                if content_type == "text/csv":
                    df = pd.read_csv(file_path,encoding='utf-8')
                    # Replace NaN values with None before converting to dict
                    df = df.replace({np.nan: None})
                    table_name = filename.split(".")[0]

                    db_name = crud.database.get(db=db,id=db_id).name

                    table = crud.indexed_table.get_table_by_name_and_db_id(db=db,name=table_name,db_id=db_id)
                    if not table:
                        table = crud.indexed_table.create(
                            db=db,
                            obj_in=schemas.IndexedTableCreate(
                                name=table_name,
                                db_id=db_id
                            )
                        )
                    
                    
                    # Get column names and first 5 rows for metadata
                    columns = df.columns.tolist()
                    # Create a copy of first 5 rows and truncate long values
                    sample_df = df.head(5).copy()
                    for column in sample_df.columns:
                        sample_df[column] = sample_df[column].apply(
                            lambda x: str(x)[:100] + '...' if isinstance(x, str) and len(str(x)) > 100 else x
                        )
                    
                    sample_data = sample_df.to_dict(orient='records')

                    # generate table synonyms, column synonyms, table descriptions and column descriptions
                    table_synonyms = index_data.generate_table_synonyms(table_name=table_name,column_names=columns,data=sample_data)
                    column_synonyms = index_data.generate_column_synonyms(table_name=table_name,column_names=columns,data=sample_data)
                    table_description = index_data.generate_table_descriptions(table_name=table_name,column_names=columns,data=sample_data)
                    column_description = index_data.generate_column_descriptions(table_name=table_name,column_names=columns,data=sample_data)
                    print(table_synonyms.table_synonyms,"this is the table synonyms")
                    print(type(table_synonyms.table_synonyms),"this is the type of the table synonyms")
                    # index into the meilisearch
                    unique_ids = [str(uuid.uuid4()) for _ in range(len(table_synonyms.table_synonyms))]
                    table_synonyms_with_ids = []
                    for i in range(len(table_synonyms.table_synonyms)):
                        table_synonym = {
                            "id": str(unique_ids[i]),
                            "table_id": str(table.id),
                            "synonym": table_synonyms.table_synonyms[i]
                        }
                        table_synonyms_with_ids.append(table_synonym)

                    print(table_synonyms_with_ids,"this is the table synonyms to be indexed into meilisearch")
                    crud.meilisearch.add_rows_to_index(index_name=f"{table_name}_synonyms",rows=table_synonyms_with_ids,primary_key="id")
                    crud.meilisearch.add_rows_to_index(index_name=f"{table_name}_table",rows=[{"id": str(table.id), "table_name": table_name}],primary_key="id")
                    # column_synonyms = index_data.generate_column_synonyms(table_name=table_name,column_names=columns,data=sample_data)
                    # print(column_synonyms,"this is the column synonyms")
                    # table_description = index_data.generate_table_descriptions(table_name=table_name,column_names=columns,data=sample_data)
                    # print(table_description,"this is the table description")
                    # column_description = index_data.generate_column_descriptions(table_name=table_name,column_names=columns,data=sample_data)
                    # print(column_description,"this is the column description")
                    print(table_name,"table synonyms indexed into meilisearch")

                    
                    # Continue with existing processing
                    data = df.to_dict(orient='records')
                    
                    
                    
                    unique_ids = [str(uuid.uuid4()) for _ in range(len(data))]
                    for i in range(len(data)):
                        data[i]["id"] = unique_ids[i]
                    
                    crud.meilisearch.add_rows_to_index(index_name=f"{table_name}_data",rows=data,primary_key="id")
                elif content_type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
                    data = excel_file_parser.execute(file_path=file_path,is_csv=False)
                    data = data["dataframes"]
                    for sheet_name,df_dict in data.items():
                        for table_name,df in df_dict.items():
                            print(table_name,"this is the table name")
                            print(df,"this is the dataframe")
                            print(sheet_name,"this is the sheet name")
                            # Sanitize the table name for Meilisearch
                            sanitized_filename = filename.split(".")[0].replace(" ", "_")
                            index_name = f"{table_name}_{sheet_name}_{sanitized_filename}"
                            # Replace any remaining invalid characters
                            index_name = re.sub(r'[^a-zA-Z0-9_-]', '_', index_name)
                            
                            # check if the table already exists
                            table = crud.indexed_table.get_table_by_name_and_db_id(db=db,name=index_name,db_id=db_id)
                            if not table:
                                # create table from the name of the file
                                table = crud.indexed_table.create(db=db,obj_in=schemas.IndexedTableCreate(name=index_name,db_id=db_id))
                            
                            # index into the meilisearch
                            # generate the unique id for each row
                            unique_ids = [str(uuid.uuid4()) for _ in range(len(df))]
                            # add the unique ids to the data using loc accessor
                            df.loc[:, 'id'] = unique_ids
                            # Convert DataFrame to records for meilisearch
                            df = df.replace({np.nan: None})
                            records = df.to_dict('records')
                            print(records,"this is the records")
                            crud.meilisearch.add_rows_to_index(index_name=index_name,rows=records,primary_key="id")
                else:
                    raise ValueError(f"File type {content_type} is not supported. Only CSV and Excel files are supported.")
            except Exception as e:
                print(f"Error processing file {filename}: {str(e)}")
                if self.request.retries >= self.max_retries - 1:  # If this is the last retry
                    # Delete the file even if processing failed after all retries
                    if file_path.exists():
                        file_path.unlink()
                raise  # Re-raise the exception for retry handling
            else:
                # Delete file after successful processing
                if file_path.exists():
                    file_path.unlink()
        
        return {"status": "success"}
    
    except Exception as e:
        print(f"Error processing files: {str(e)}")
        # raise self.retry(exc=e)

@app.task
def process_term_search(search_id: str, search_term: str, table_ids: List[str] = None, exact_match: bool = False):
    """
    Process a term search asynchronously
    """
    search_result = None
    try:
        db = next(deps.get_db())
        
        # For exact matching, wrap the search term in quotes
        search_query = f'"{search_term}"' if exact_match else search_term
        
        if table_ids:
            index_name = table_ids[0] if table_ids else "kp_employee"
            meiliresults = crud.meilisearch.search(
                index_name=index_name,
                search_query=search_query
            )
        else:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {os.getenv("MEILISEARCH_API_KEY")}'
            }
            
            try:
                search_queries = []
                indexes = crud.meilisearch.get_all_indexes()
                
                for index in indexes.get("results"):
                    query = {
                        'indexUid': index.uid,
                        'q': search_query,
                        'limit': 50,
                        # Add exact match settings
                        'matchingStrategy': 'all' if exact_match else 'last',
                        'attributesToSearchOn': ['*']
                    }
                    search_queries.append(query)
                
                url = "http://meilisearch:7700/multi-search"
                payload = json.dumps({
                    "queries": search_queries
                })

                response = requests.request("POST", url, headers=headers, data=payload)
                results = response.json()
                
                meiliresults = []
                for result in results.get("results"):
                    if not result.get("hits"):
                        continue
                    meiliresults.append({
                        "table_name": result.get("indexUid"),
                        "result_data": result.get("hits")
                    })
                
            except Exception as e:
                # Fallback to single index search
                meiliresults = crud.meilisearch.search(
                    index_name="kp_employee",
                    search_query=search_query
                )
        
        # Update the search result
        search_result = crud.search_result.get_by_column_first(
            db=db,
            filter_column="search_id",
            filter_value=search_id
        )
        
        if search_result:
            crud.search_result.update(
                db=db,
                db_obj=search_result,
                obj_in=schemas.SearchResultUpdate(
                    result=meiliresults,
                    status="success",
                    search_text=search_term
                )
            )
            
    except Exception as e:
        # Update search result with error status
        if search_result:
            crud.search_result.update(
                db=db,
                db_obj=search_result,
                obj_in=schemas.SearchResultUpdate(
                    status="failed",
                    extras={"error": str(e)}
                )
            )
        raise
        
    finally:
        db.close()



@app.task
def generate_metadata(search_id: str, search_term: str, table_ids: List[str] = None, exact_match: bool = False):
    """
    Process a term search asynchronously
    """
    search_result = None
    try:
        db = next(deps.get_db())
        
        # For exact matching, wrap the search term in quotes
        search_query = f'"{search_term}"' if exact_match else search_term
        
        if table_ids:
            index_name = table_ids[0] if table_ids else "kp_employee"
            meiliresults = crud.meilisearch.search(
                index_name=index_name,
                search_query=search_query
            )
        else:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {os.getenv("MEILISEARCH_API_KEY")}'
            }
            
            try:
                search_queries = []
                indexes = crud.meilisearch.get_all_indexes()
                
                for index in indexes.get("results"):
                    query = {
                        'indexUid': index.uid,
                        'q': search_query,
                        'limit': 50,
                        # Add exact match settings
                        'matchingStrategy': 'all' if exact_match else 'last',
                        'attributesToSearchOn': ['*']
                    }
                    search_queries.append(query)
                
                url = "http://meilisearch:7700/multi-search"
                payload = json.dumps({
                    "queries": search_queries
                })

                response = requests.request("POST", url, headers=headers, data=payload)
                results = response.json()
                
                meiliresults = []
                for result in results.get("results"):
                    if not result.get("hits"):
                        continue
                    meiliresults.append({
                        "table_name": result.get("indexUid"),
                        "result_data": result.get("hits")
                    })
                
            except Exception as e:
                # Fallback to single index search
                meiliresults = crud.meilisearch.search(
                    index_name="kp_employee",
                    search_query=search_query
                )
        
        # Update the search result
        search_result = crud.search_result.get_by_column_first(
            db=db,
            filter_column="search_id",
            filter_value=search_id
        )
        
        if search_result:
            crud.search_result.update(
                db=db,
                db_obj=search_result,
                obj_in=schemas.SearchResultUpdate(
                    result=meiliresults,
                    status="success",
                    search_text=search_term
                )
            )
            
    except Exception as e:
        # Update search result with error status
        if search_result:
            crud.search_result.update(
                db=db,
                db_obj=search_result,
                obj_in=schemas.SearchResultUpdate(
                    status="failed",
                    extras={"error": str(e)}
                )
            )
        raise
        
    finally:
        db.close()




