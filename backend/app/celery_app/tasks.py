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
from abc import ABC, abstractmethod
from app.core.security import settings
from typing import List
import datetime
from pydantic import UUID4

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
def run_sql_query(self, search_id, query):
    try:
        db = next(deps.get_db())
        if not query or not isinstance(query, list):
            raise ValueError("Query must be a non-empty list")
            
        sql = query[0]
        print(f"Task {search_id}: Running query: {sql}")
        
        # Execute query and get results
        query_result = [dict(row._mapping) for row in db.execute(text(sql)).fetchall()]
        result = {
            "table_name": extract_table_names(sql),
            "result_data": query_result
        }
        
        # Get current results and append new result
        search_result = crud.search_result.get_by_column_first(db=db,filter_column="search_id",filter_value=search_id)
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
    

def _build_search_query(search_term: str, exact_match: bool) -> str:
    """Build the search query string with exact match handling"""
    return f'"{search_term}"' if exact_match else search_term

def _create_query_dict(index_uid: str, search_query: str, exact_match: bool, skip: int = 0, limit: int = 20,attributes_to_search_on:List[str] = ["*"]) -> dict:
    """Create a single query dictionary for Meilisearch with pagination"""
    return {
        'indexUid': index_uid,
        'q': search_query,
        'limit': limit,
        'offset': skip,
        'attributesToSearchOn': attributes_to_search_on
    }

def _get_meilisearch_headers() -> dict:
    """Get headers for Meilisearch API requests"""
    return {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {settings.MEILI_MASTER_KEY}'
    }

def _execute_multi_search(search_queries: List[dict], headers: dict) -> List[dict]:
    """Execute multi-search request to Meilisearch"""
    url = "http://meilisearch:7700/multi-search"
    
    payload = json.dumps({"queries": search_queries})

    print(payload,"thisi is the payload")
    
    response = requests.request("POST", url, headers=headers, data=payload)
    results = response.json()
    print(results,"these are results")
    
    meiliresults = []
    for result in results.get("results", []):
        if not result.get("hits"):
            continue
        meiliresults.append({
            "table_name": result.get("indexUid"),
            "result_data": result.get("hits"),
            "total_hits": result.get("estimatedTotalHits", 0)  # Add total hits count
        })
    return meiliresults

def _update_search_result(
    db, 
    search_result, 
    meiliresults: List[dict], 
    search_term: str, 
    exact_match: bool,
    table_ids: List[str] = None,
    error: str = None,
    extras: dict = None
):
    """Update the search result in the database"""
    if not search_result:
        return
        
    if error:
        update_data = schemas.SearchResultUpdate(
            status="failed",
            extras={"error": error}
        )
    else:
        update_data = schemas.SearchResultUpdate(
            result=meiliresults,
            status="success",
            search_text=search_term,
            extras=extras or {
                "exact_match": exact_match,
                "table_ids": table_ids
            }
        )
    
    crud.search_result.update(
        db=db,
        db_obj=search_result,
        obj_in=update_data
    )

@app.task
def process_term_search(
    role_id: UUID4,
    search_id: str, 
    search_term: str, 
    table_ids: List[str] = None, 
    exact_match: bool = False,
    skip: int = 0,
    limit: int = 20
):
    """Process a term search asynchronously with pagination for specific table"""
    print(role_id,"this is role id")
    search_result = None
    db = next(deps.get_db())
    
    try:
        search_query = _build_search_query(search_term, exact_match)
        headers = _get_meilisearch_headers()
        search_queries = []

        # Get existing search result first
        search_result = crud.search_result.get_by_column_first(
            db=db,
            filter_column="search_id",
            filter_value=search_id
        )

        # If table_ids contains exactly one table, we're doing single table pagination
        if table_ids and len(table_ids) == 1:
            tables = crud.indexed_table.get_tables_by_ids(db=db, table_ids=table_ids)
            table_name = tables[0].name
            display_name = tables[0].display_name
            attributes_for_role = ["*"]
            attributes_to_retrieve = tables[0].attributes_to_retrieve
            print(attributes_to_retrieve,"these are attributes to retrieve")
            if attributes_to_retrieve:
                attributes_for_role = attributes_to_retrieve.get(str(role_id))
                print(attributes_for_role,"these are attributes for role")
            search_queries.append(_create_query_dict(
                table_name, 
                search_query, 
                exact_match,
                skip,
                limit,
                attributes_for_role
            ))
            
            # Execute search for single table
            meiliresults = _execute_multi_search(search_queries, headers)
            
            if search_result and search_result.result:
                existing_results = search_result.result
                existing_table = next(
                    (result for result in existing_results if result.get("table_name") == table_name),
                    None
                )
                
                if meiliresults:
                    new_table_data = meiliresults[0]
                    
                    if existing_table:
                        # Append new data to existing table
                        existing_table["result_data"].extend(new_table_data["result_data"])
                        existing_table["total_hits"] = new_table_data["total_hits"]
                        existing_table["pagination"] = {
                            "skip": skip,
                            "limit": limit,
                        }
                        existing_table["table_id"] = table_ids[0]
                        existing_table["display_name"] = display_name
                    else:
                        # Add pagination info to new table data
                        new_table_data["pagination"] = {
                            "skip": skip,
                            "limit": limit,
                        }
                        new_table_data["table_id"] = table_ids[0]
                        new_table_data["display_name"] = display_name
                        # Add the new table data to existing results
                        existing_results.append(new_table_data)
                    
                    meiliresults = existing_results
        else:
            # Original multi-table search logic
            if table_ids:
                tables = crud.indexed_table.get_tables_by_ids(db=db, table_ids=table_ids)
                for table in tables:
                    #TODO: remove these conditionals
                    if table.name in ["kp_employee", "name_age_rank"]:
                        attributes_to_retrieve = table.attributes_to_retrieve
                        print(attributes_to_retrieve,"these are attributes to retrieve")
                        attributes_for_role = ["*"]
                        if attributes_to_retrieve:
                            attributes_for_role = attributes_to_retrieve.get(str(role_id))
                            print(attributes_for_role,"these are attributes for role")
                        search_queries.append(_create_query_dict(
                            table.name, 
                            search_query, 
                            exact_match,
                            skip,
                            limit,
                            attributes_for_role
                        ))
            else:
                tables = crud.indexed_table.get_tables_by_role(db=db,role_id=role_id)
                for table in tables:
                    attributes_to_retrieve = table.attributes_to_retrieve
                    print(attributes_to_retrieve,"these are attributes to retrieve")
                    attributes_for_role = ["*"]
                    if attributes_to_retrieve:
                        attributes_for_role = attributes_to_retrieve.get(str(role_id))
                        print(attributes_for_role,"these are attributes for role")
                    #TODO: remove these conditionals
                    if table.name in ["kp_employee", "name_age_rank"]:
                        search_queries.append(_create_query_dict(
                            table.name, 
                            search_query, 
                            exact_match,
                            skip,
                            limit,
                            attributes_for_role
                        ))

            # Create a mapping of table names to their IDs
            table_name_to_id = {table.name: str(table.id) for table in tables}
            table_id_to_display_name = {str(table.id): table.display_name for table in tables}
            print(table_id_to_display_name,"these are table id to display name")
            print(search_queries,"these are search queries")
            print(table_name_to_id,"these are table name to id")
            
            meiliresults = _execute_multi_search(search_queries, headers)

            print(meiliresults,"these are meiliresults")
            
            # Add pagination info and table_id to each table's results
            for result in meiliresults:
                result["pagination"] = {
                    "skip": skip,
                    "limit": limit,
                }
                result["table_id"] = table_name_to_id.get(result["table_name"])
                result["display_name"] = table_id_to_display_name.get(result["table_id"])
                print(result, "this is the result new")


        # Update extras
        extras = {
            **(search_result.extras or {}),
            "exact_match": exact_match,
            "table_ids": table_ids,
        }

        _update_search_result(
            db, 
            search_result, 
            meiliresults, 
            search_term,
            exact_match,
            table_ids,
            extras=extras
        )
            
    except Exception as e:
        _update_search_result(
            db, 
            search_result, 
            [], 
            search_term, 
            exact_match,
            table_ids,
            error=str(e)
        )
        raise
    
    finally:
        db.close()



@app.task(bind=True)
def execute_meilisearch_query(self,role_id,search_id,search_query ,queries,table_ids,skip,limit):
    search_result = None
    db = next(deps.get_db())

    
    try:
        headers = _get_meilisearch_headers()
        search_result = crud.search_result.get_by_column_first(db=db,filter_column="search_id",filter_value=search_id)

        if table_ids and len(table_ids) == 1:
            tables = crud.indexed_table.get_tables_by_ids(db=db, table_ids=table_ids)
            table_name = tables[0].name
            display_name = tables[0].display_name
            meiliresults = _execute_multi_search(queries, headers)
            if search_result and search_result.result:
                existing_results = search_result.result
                existing_table = next(
                    (result for result in existing_results if result.get("table_name") == table_name),
                    None
                )
                
                if meiliresults:
                    new_table_data = meiliresults[0]
                    
                    if existing_table:
                        # Append new data to existing table
                        existing_table["result_data"].extend(new_table_data["result_data"])
                        existing_table["total_hits"] = new_table_data["total_hits"]
                        existing_table["pagination"] = {
                            "skip": skip,
                            "limit": limit,
                        }
                        existing_table["table_id"] = table_ids[0]
                        existing_table["display_name"] = display_name
                    else:
                        # Add pagination info to new table data
                        new_table_data["pagination"] = {
                            "skip": skip,
                            "limit": limit,
                        }
                        new_table_data["table_id"] = table_ids[0]
                        new_table_data["display_name"] = display_name
                        # Add the new table data to existing results
                        existing_results.append(new_table_data)
                    
                    meiliresults = existing_results

        else:
            if table_ids:
                tables = crud.indexed_table.get_tables_by_ids(db=db, table_ids=table_ids)
                meiliresults = _execute_multi_search(queries, headers)
            else:
                tables = crud.indexed_table.get_tables_by_role(db=db,role_id=role_id)
                meiliresults = _execute_multi_search(queries, headers)


        
            print(search_result,"this is the search result")
            table_name_to_id = {table.name: str(table.id) for table in tables}
            table_id_to_display_name = {str(table.id): table.display_name for table in tables}


            # Add pagination info and table_id to each table's results
            for result in meiliresults:
                result["pagination"] = {
                    "skip": skip,
                    "limit": limit,
                }
                result["table_id"] = table_name_to_id.get(result["table_name"])
                result["display_name"] = table_id_to_display_name.get(result["table_id"])
                print(result, "this is the result new")


        # Update extras
        extras = {
            **(search_result.extras or {}),
            "exact_match": False,
            "table_ids": table_ids,
        }

        _update_search_result(
            db, 
            search_result, 
            meiliresults, 
            search_term=search_query,
            exact_match=False,
            table_ids=table_ids,
            extras=extras
        )
            
            
            
    except Exception as e:
        print(e,"this is the error")
        _update_search_result(
            db, 
            search_result, 
            [], 
            search_term=search_query, 
            exact_match=False,
            table_ids=table_ids,
            error=str(e)
        )
        raise
    
    finally:
        db.close()



class DataProcessor(ABC):
    @abstractmethod
    def process(self, file_path: Path, filename: str) -> list[tuple[str, pd.DataFrame]]:
        """Process the data file and return list of (table_name, processed_dataframe)"""
        pass

class CSVProcessor(DataProcessor):
    def process(self, file_path: Path, filename: str) -> list[tuple[str, pd.DataFrame]]:
        df = pd.read_csv(file_path, encoding='utf-8')
        df = df.replace({np.nan: None})
        table_name = filename.split(".")[0]
        return [(table_name, df)]

class ExcelProcessor(DataProcessor):
    def process(self, file_path: Path, filename: str) -> list[tuple[str, pd.DataFrame]]:
        data = excel_file_parser.execute(file_path=file_path, is_csv=False)
        sanitized_filename = filename.split(".")[0].replace(" ", "_")
        
        results = []
        for sheet_name, df_dict in data["dataframes"].items():
            for table_name, df in df_dict.items():
                index_name = f"{table_name}_{sheet_name}_{sanitized_filename}"
                index_name = re.sub(r'[^a-zA-Z0-9_-]', '_', index_name)
                df = df.replace({np.nan: None})
                results.append((index_name, df))
        return results

class DataFrameProcessor:
    @staticmethod
    def get_sample_data(df: pd.DataFrame, sample_size: int = 5) -> list:
        sample_df = df.head(sample_size).copy()
        for column in sample_df.columns:
            sample_df[column] = sample_df[column].apply(
                lambda x: str(x)[:100] + '...' if isinstance(x, str) and len(str(x)) > 100 else x
            )
        return sample_df.to_dict(orient='records')
    
    @staticmethod
    def get_columns_data(df: pd.DataFrame, unique_limit: int = 5) -> dict:
        return {
            column: df[column].unique().tolist()[:unique_limit] 
            for column in df.columns
        }

def _process_dataframe(db, db_id: str, table_name: str, df: pd.DataFrame, df_processor: DataFrameProcessor):
    """Process a single dataframe and create/update table and column records"""
    # Generate sample data and column metadata
    sample_data = df_processor.get_sample_data(df)
    columns_data = df_processor.get_columns_data(df)

    # Create or update table
    table_result = crud.indexed_table.get_table_by_name_and_db_id(
        db=db, name=table_name, db_id=db_id
    )
    
    table_result = (
        crud.indexed_table.create(
            db=db,
            obj_in=schemas.IndexedTableCreate(
                name=table_name,
                db_id=db_id,
                sample_data=sample_data
            )
        ) if not table_result else
        crud.indexed_table.update(
            db=db,
            db_obj=table_result,
            obj_in=schemas.IndexedTableUpdate(
                sample_data=sample_data
            )
        )
    )

    if not table_result:
        raise ValueError(f"Table {table_name} could not be indexed")
    
    return table_result, columns_data

def _process_columns(db, table_result, columns_data: dict):
    """Process columns for a table"""
    for column_name, unique_vals in columns_data.items():
        # Truncate long string values
        unique_vals = [
            str(val)[:100] + '...' if isinstance(val, str) and len(str(val)) > 100 
            else val 
            for val in unique_vals
        ]
        
        column_obj = crud.indexed_table_column.get_column_by_name_and_table_id(
            db=db, 
            name=column_name, 
            table_id=table_result.id
        )
        
        if not column_obj:
            crud.indexed_table_column.create(
                db=db,
                obj_in=schemas.IndexedTableColumnCreate(
                    name=column_name,
                    table_id=table_result.id,
                    unique_values=unique_vals
                )
            )
        else:
            crud.indexed_table_column.update(
                db=db,
                db_obj=column_obj,
                obj_in=schemas.IndexedTableColumnUpdate(
                    unique_values=unique_vals
                )
            )

def _index_in_meilisearch(df: pd.DataFrame, table_name: str):
    """Index dataframe in Meilisearch"""
    data = df.to_dict('records')
    unique_ids = [str(uuid.uuid4()) for _ in range(len(data))]
    
    for i, record in enumerate(data):
        record["id"] = unique_ids[i]
        # Convert non-serializable objects to strings
        for key, value in record.items():
            if isinstance(value, (datetime.datetime, datetime.date)):
                record[key] = value.isoformat()
            elif isinstance(value, datetime.time):
                record[key] = value.strftime('%H:%M:%S')  # Convert time to string
            elif isinstance(value, bytes):
                record[key] = value.decode('utf-8', errors='ignore')  # Convert bytes to string
            elif not isinstance(value, (str, int, float, bool, type(None))):
                record[key] = str(value)  # Fallback conversion to string for other types
    
    crud.meilisearch.add_rows_to_index(
        index_name=table_name,
        rows=data,
        primary_key="id"
    )

def _process_single_file(db, db_id: str, file_info: dict, processors: dict, df_processor: DataFrameProcessor):
    """Process a single file"""
    file_path = Path(file_info["path"])
    content_type = file_info["content_type"]
    filename = file_info["filename"]
    
    processor = processors.get(content_type)
    if not processor:
        raise ValueError(f"File type {content_type} is not supported")
    
    try:
        # Process the file and get all dataframes
        table_dfs = processor.process(file_path, filename)
        
        # Process each resulting dataframe
        for table_name, df in table_dfs:
            # Process dataframe and get table result
            table_result, columns_data = _process_dataframe(db, db_id, table_name, df, df_processor)
            
            # Process columns
            _process_columns(db, table_result, columns_data)
            
            # Index in Meilisearch
            _index_in_meilisearch(df, table_name)
            
            # Generate metadata asynchronously
            # generate_metadata.apply_async(args=[db_id, table_result.id])
        
        return True
    finally:
        if file_path.exists():
            file_path.unlink()

@app.task(bind=True, max_retries=3)
def index_data_file(self, db_id: str, saved_files: List[dict]):
    """Index data files"""
    db = next(deps.get_db())
    processors = {
        "text/csv": CSVProcessor(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ExcelProcessor(),
        "application/vnd.ms-excel": ExcelProcessor()
    }
    df_processor = DataFrameProcessor()
    
    try:
        for file_info in saved_files:
            try:
                _process_single_file(db, db_id, file_info, processors, df_processor)
            except Exception as e:
                print(f"Error processing file {file_info['filename']}: {str(e)}")
                if self.request.retries >= self.max_retries - 1:
                    file_path = Path(file_info["path"])
                    if file_path.exists():
                        file_path.unlink()
                raise
        
        return {"status": "success"}
    
    except Exception as e:
        print(f"Error processing files: {str(e)}")
        raise self.retry(exc=e)
    finally:
        db.close()





@app.task(bind=True, max_retries=3)
def generate_metadata(self, db_id: str, table_id: str):
    """Coordinator task that triggers table and column metadata generation"""
    try:
        
        # Trigger table and column metadata generation tasks
        generate_table_metadata.apply_async(args=[str(table_id)])
        generate_column_metadata.apply_async(args=[str(table_id)])
        
        return {"status": "success", "message": "Metadata generation tasks initiated"}
        
    except Exception as e:
        print(f"Error in generate_metadata coordinator: {str(e)}")
        raise

@app.task(bind=True, max_retries=3)
def generate_table_metadata(self, table_id: str):
    """Generate and index table-level metadata"""
    try:
        db = next(deps.get_db())
        table = crud.indexed_table.get(db=db, id=table_id)
        columns = crud.indexed_table_column.get_columns_by_table_id(db=db, table_id=table_id)
        
        table_name = table.name
        columns = [column[0] for column in columns]
        sample_data = table.sample_data

        # Generate table metadata
        try:
            table_synonyms = index_data.generate_table_synonyms(table_name, columns, sample_data)
            if table_synonyms.table_synonyms:
                index_table_synonyms.apply_async(
                    args=[table_id, table_name, table_synonyms.table_synonyms],
                    countdown=5
                )
        except Exception as e:
            print(f"Error generating table synonyms: {str(e)}")

        try:
            table_description = index_data.generate_table_description(table_name, columns, sample_data)
            if table_description.table_description:
                index_table_description.apply_async(
                    args=[table_id, table_name, table_description.table_description],
                    countdown=5
                )
        except Exception as e:
            print(f"Error generating table description: {str(e)}")

        return {"status": "success", "table_name": table_name}
    except Exception as e:
        print(f"Error in generate_table_metadata: {str(e)}")
        retry_in = (2 ** self.request.retries) * 60
        raise self.retry(exc=e, countdown=retry_in)
    finally:
        db.close()

@app.task(bind=True, max_retries=3)
def generate_column_metadata(self, table_id: str):
    """Generate and index column-level metadata"""
    try:
        db = next(deps.get_db())
        table = crud.indexed_table.get(db=db, id=table_id)
        columns = crud.indexed_table_column.get_columns_by_table_id(db=db, table_id=table_id)
        
        table_name = table.name
        sample_data = table.sample_data

        # Generate column metadata
        try:

            for column in columns:
                column_name = column.name
                unique_values = column.unique_values
                print(column_name, "this is the column name")
                column_synonyms = index_data.generate_column_synonyms(table_name, column_name, sample_data, unique_values)
                column_description = index_data.generate_column_description(table_name, column_name, sample_data, unique_values)
                column_id = str(column.id)


                print(column_synonyms.column_synonyms,"this is the column synonyms")
                print(column_description.column_description,"this is the column description")

                if column_name:
                    index_column.apply_async(
                        args=[table_id, table_name, column_name, column_id],
                        countdown=5
                    )

                if column_synonyms.column_synonyms:
                    index_column_synonyms.apply_async(
                        args=[table_id, table_name, column_name, column_synonyms.column_synonyms[column_name], column_id],
                        countdown=5
                    )

                if column_description.column_description:
                    index_column_description.apply_async(
                        args=[table_id, table_name, column_name, column_description.column_description, column_id],
                        countdown=5
                    )
        except Exception as e:
            print(f"Error generating column metadata: {str(e)}")
            raise

        return {"status": "success", "table_name": table_name}
    except Exception as e:
        print(f"Error in generate_column_metadata: {str(e)}")
        retry_in = (2 ** self.request.retries) * 60
        raise self.retry(exc=e, countdown=retry_in)
    finally:
        db.close()




@app.task
def index_table_in_meilisearch(table_id: str,table_name: str):
    """Index main table data to Meilisearch"""
    try:
        table_data = {
            "id": table_id,
            "table_name": table_name
        }
        
        crud.meilisearch.add_rows_to_index(
            index_name=f"{table_name}_table", 
            rows=[table_data],
            primary_key="id"
        )
        return {"status": "success", "table_name": table_name}
    except Exception as e:
        print(f"Error indexing table data: {str(e)}")
        raise

@app.task
def index_table_synonyms(table_id: str,table_name: str,table_synonyms: list):
    """Index table synonyms to Meilisearch"""
    try:
        
        unique_ids = [str(uuid.uuid4()) for _ in range(len(table_synonyms))]
        table_synonyms_with_ids = [
            {
                "id": str(uid),
                "table_id": table_id,
                "synonym": synonym
            }
            for uid, synonym in zip(unique_ids, table_synonyms)
        ]
        
        crud.meilisearch.add_rows_to_index(
            index_name=f"{table_name}_synonyms",
            rows=table_synonyms_with_ids,
            primary_key="id"
        )
        return {"status": "success", "table_name": table_name}
    except Exception as e:
        print(f"Error indexing table synonyms: {str(e)}")
        raise

@app.task
def index_table_description_in_meilisearch(table_id: str,table_name: str,table_description: str):
    """Index table description to Meilisearch"""
    try:        
        description_data = {
            "id": str(uuid.uuid4()),
            "table_id": table_id,
            "description": table_description
        }
        
        crud.meilisearch.add_rows_to_index(
            index_name=f"{table_name}_description",
            rows=[description_data],
            primary_key="id"
        )
        return {"status": "success", "table_name": table_name}
    except Exception as e:
        print(f"Error indexing table description: {str(e)}")
        raise

@app.task
def index_column_in_meilisearch(table_id: str, table_name: str, column_name: str, id: str):
    """Index basic column data to Meilisearch"""
    try:
        column_data = {
            "id": id,
            "table_id": table_id, 
            "column_name": column_name
        }
        
        crud.meilisearch.add_rows_to_index(
            index_name=f"{table_name}_columns",
            rows=[column_data],
            primary_key="id"
        )
        return {"status": "success", "table_name": table_name, "column_name": column_name}
    except Exception as e:
        print(f"Error indexing column data: {str(e)}")
        raise

@app.task 
def index_column_synonyms(table_id: str, table_name: str, column_name: str, synonyms: list, column_id: str):
    """Index column synonyms to Meilisearch"""
    try:
        unique_ids = [str(uuid.uuid4()) for _ in range(len(synonyms))]
        synonym_data = [
            {
                "id": str(uid),
                "table_id": table_id,
                "synonym": synonym,
                "column_id": column_id
            }
            for uid, synonym in zip(unique_ids, synonyms)
        ]
        
        crud.meilisearch.add_rows_to_index(
            index_name=f"{table_name}_column_synonyms",
            rows=synonym_data,
            primary_key="id"
        )
        return {"status": "success", "table_name": table_name, "column_name": column_name}
    except Exception as e:
        print(f"Error indexing column synonyms: {str(e)}")
        raise

@app.task
def index_column_description(table_id: str, table_name: str, column_name: str, description: str, column_id: str):
    """Index column description to Meilisearch"""
    try:
        description_data = {
            "id": str(uuid.uuid4()),
            "table_id": table_id,
            "column_name": column_name,
            "description": description,
            "column_id": column_id
        }
        
        crud.meilisearch.add_rows_to_index(
            index_name=f"{table_name}_column_descriptions",
            rows=[description_data],
            primary_key="id"
        )
        return {"status": "success", "table_name": table_name, "column_name": column_name}
    except Exception as e:
        print(f"Error indexing column description: {str(e)}")
        raise

