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
    

def _build_search_query(search_term: str, exact_match: bool) -> str:
    """Build the search query string with exact match handling"""
    return f'"{search_term}"' if exact_match else search_term

def _create_query_dict(index_uid: str, search_query: str, exact_match: bool) -> dict:
    """Create a single query dictionary for Meilisearch"""
    return {
        'indexUid': index_uid,
        'q': search_query,
        'limit': 50,
        'matchingStrategy': 'all' if exact_match else 'last',
        'attributesToSearchOn': ['*']
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
    
    response = requests.request("POST", url, headers=headers, data=payload)
    results = response.json()
    
    meiliresults = []
    for result in results.get("results", []):
        if not result.get("hits"):
            continue
        meiliresults.append({
            "table_name": result.get("indexUid"),
            "result_data": result.get("hits"),
        })
    return meiliresults

def _update_search_result(db, search_result, meiliresults: List[dict], search_term: str, error: str = None):
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
            search_text=search_term
        )
    
    crud.search_result.update(
        db=db,
        db_obj=search_result,
        obj_in=update_data
    )

@app.task
def process_term_search(search_id: str, search_term: str, table_ids: List[str] = None, exact_match: bool = False):
    """Process a term search asynchronously"""
    search_result = None
    db = next(deps.get_db())
    
    try:
        search_query = _build_search_query(search_term, exact_match)
        headers = _get_meilisearch_headers()
        search_queries = []

        if table_ids:
            # Search specific tables
            tables = crud.indexed_table.get_tables_by_ids(db=db, table_ids=table_ids)
            for table in tables:
                search_queries.append(_create_query_dict(table.name, search_query, exact_match))
        else:
            # Search all indexes
            indexes = crud.meilisearch.get_all_indexes()
            for index in indexes.get("results", []):
                search_queries.append(_create_query_dict(index.uid, search_query, exact_match))

        meiliresults = _execute_multi_search(search_queries, headers)
        
        # Get and update search result
        search_result = crud.search_result.get_by_column_first(
            db=db,
            filter_column="search_id",
            filter_value=search_id
        )
        _update_search_result(db, search_result, meiliresults, search_term)
            
    except Exception as e:
        _update_search_result(db, search_result, [], search_term, str(e))
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
            file_path = Path(file_info["path"])
            content_type = file_info["content_type"]
            filename = file_info["filename"]
            
            try:
                processor = processors.get(content_type)
                if not processor:
                    raise ValueError(f"File type {content_type} is not supported")
                
                # Process the file and get all dataframes
                table_dfs = processor.process(file_path, filename)
                
                # Process each resulting dataframe
                for table_name, df in table_dfs:
                    # Generate sample data and column metadata
                    sample_data = df_processor.get_sample_data(df)
                    columns_data = df_processor.get_columns_data(df)
                    
                    # Generate metadata asynchronously
                    generate_metadata.apply_async(
                        args=[
                            db_id,
                            table_name,
                            sample_data,
                            columns_data
                        ]
                    )
                
            except Exception as e:
                print(f"Error processing file {filename}: {str(e)}")
                if self.request.retries >= self.max_retries - 1:
                    if file_path.exists():
                        file_path.unlink()
                raise
            else:
                if file_path.exists():
                    file_path.unlink()
        
        return {"status": "success"}
    
    except Exception as e:
        print(f"Error processing files: {str(e)}")
        raise self.retry(exc=e)





@app.task(bind=True, max_retries=3)
def generate_metadata(self, db_id: str, table_name: str, sample_data: list, columns_data: dict):
    """Coordinator task that triggers table and column metadata generation"""
    try:
        db = next(deps.get_db())
        
        # First index/update the table in DB and get the table object
        table_result = index_table_in_db.delay(
            db_id=db_id,
            table_name=table_name,
            sample_data=sample_data
        ).get()
        
        if not table_result:
            raise ValueError(f"Table {table_name} could not be indexed")
            
        # Index columns with unique values
        index_table_columns_in_db.delay(
            table_id=table_result["table_id"],
            columns_data=columns_data
        ).get()

        # Trigger table metadata generation
        generate_table_metadata.apply_async(args=[table_result["table_id"]])
        
        # Trigger column metadata generation
        generate_column_metadata.apply_async(args=[table_result["table_id"]])
        
        return {"status": "success", "message": "Metadata generation tasks initiated"}
    except Exception as e:
        print(f"Error in generate_metadata coordinator: {str(e)}")
        raise
    finally:
        db.close()

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
def index_table_in_db(db_id: str,table_name: str,sample_data: list):
    """Index main table data to DB"""
    try:
        db = next(deps.get_db())
        table = crud.indexed_table.get_table_by_name_and_db_id(db=db,name=table_name,db_id=db_id)
        if not table:
            table = crud.indexed_table.create(
                db=db,
                obj_in=schemas.IndexedTableCreate(
                    name=table_name,
                    db_id=db_id,
                    sample_data=sample_data
                )
            )
        else:
            table = crud.indexed_table.update(
                db=db,
                db_obj=table,
                obj_in=schemas.IndexedTableUpdate(
                    sample_data=sample_data
                )
            )
        return {"status": "success", "table_name": table_name}
    except Exception as e:
        print(f"Error indexing table data: {str(e)}")
        raise

@app.task
def index_table_columns_in_db(table_id: str, columns_data: dict):
    """Index table columns in DB"""
    try:    
        db = next(deps.get_db())
        
        # store the columns in the database
        for column_name, unique_vals in columns_data.items():
            try:
                # Truncate long string values
                unique_vals = [
                    str(val)[:100] + '...' if isinstance(val, str) and len(str(val)) > 100 
                    else val 
                    for val in unique_vals
                ]
                
                column_obj = crud.indexed_table_column.get_column_by_name_and_table_id(
                    db=db, 
                    name=column_name, 
                    table_id=table_id
                )
                
                if not column_obj:
                    column_obj = crud.indexed_table_column.create(
                        db=db,
                        obj_in=schemas.IndexedTableColumnCreate(
                            name=column_name,
                            table_id=table_id,
                            unique_values=unique_vals
                        )
                    )
                else:
                    column_obj = crud.indexed_table_column.update(
                        db=db,
                        db_obj=column_obj,
                        obj_in=schemas.IndexedTableColumnUpdate(
                            unique_values=unique_vals
                        )
                    )
            except Exception as e:
                print(f"Error indexing column {column_name}: {str(e)}")
                raise
        
        return {"status": "success", "table_id": table_id}
    except Exception as e:
        print(f"Error indexing table columns: {str(e)}")
        raise
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

