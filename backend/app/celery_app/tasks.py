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
import datetime
from app.utils.index_data import index_data
from abc import ABC, abstractmethod
from app.core.security import settings
from typing import List
from pydantic import UUID4
import copy





    

def _build_search_query(search_term: str, exact_match: bool) -> str:
    """Build the search query string with exact match handling"""
    return f'"{search_term}"' if exact_match else search_term

def _create_query_dict(index_uid: str, search_query: str, exact_match: bool, skip: int = 0, limit: int = 20,attributes_to_search_on:List[str] = ["*"],filters=None) -> dict:
    """Create a single query dictionary for Meilisearch with pagination"""
    return {
        'indexUid': index_uid,
        'q': search_query,
        'limit': limit,
        'offset': skip,
        'attributesToSearchOn': attributes_to_search_on,
        "filter": filters
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
    print(results,"these are results")
    
    meiliresults = []
    for result in results.get("results", []):
        if not result.get("hits"):
            continue
        for hit in result["hits"]:
            hit.pop("meili_id",None)
        meiliresults.append({
            "table_name": result.get("indexUid"),
            "result_data": result.get("hits"),
            "total_hits": result.get("estimatedTotalHits", 0)  # Add total hits count
        })
    return meiliresults


def _execute_search(index_name,search_query:dict, headers: dict) -> List[dict]:
    """Execute multi-search request to Meilisearch"""
    url = "http://meilisearch:7700/indexes/{0}/search".format(index_name)
    print(url,"this is the url")
    print(index_name,search_query,"this is the search query")
    payload = json.dumps(search_query)

    print(payload,"This the payload")
    
    response = requests.request("POST", url, headers=headers, data=payload)

    print(response,"this is the response")
    result = response.json()
    print(result,"these are results")
    
    meiliresults = []
    for hit in result["hits"]:
        print(hit,"this is the hit")
        hit.pop("meili_id",None)
    if result["hits"]:
        meiliresults.append({
            "table_name": index_name,
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

def identify_primary_matches(results):
    primary_matches = {}
    for result in results:
        index = result["indexUid"]
        hits = result["hits"]
        if hits:
            primary_matches[index] = hits
    return primary_matches


def fetch_related_data(db,meiliresults,relationships,skip,limit):
    related_results = {}
    print(meiliresults,"mieli is this")
    headers = _get_meilisearch_headers()
    for result in meiliresults:
        print(result,"this is the result in the meiliresult")
        table_name = result.get("table_name")
        result_data = result.get("result_data")
        print(table_name,"this is the table_name")
        print(result_data,"this is the result data")
        print(relationships,"there are the relationships")
        related_indexes = relationships.get(table_name,{})
        print(related_indexes,"this is the related indexes")
        for related_index, mapping in related_indexes.items():
            related_results[related_index] = []

            # For each hit, map related data
            for hit in result_data:
                key_value = hit[mapping["key"]]
                 # Create a filter for the related index query
                filter_condition = "{0} = '{1}'".format(mapping['foreign_key'],key_value)
                print(key_value,"this is the key value")
                query = {
                    "q":"",
                    "filter":filter_condition
                }
                print(query,"this is the query")
                related_hits = _execute_search(related_index,query, headers)
                print(related_hits,"related hits")
                if related_hits:
                    related_results[related_index].extend(related_hits)

    return related_results

def build_combined_results(primary_matches, related_results):
    combined = {}

    def add_unique_hits(existing_hits, new_hits):
        print(existing_hits,"this is the existing hits")
        print(new_hits,"this is the new hits")
        seen = {frozenset(hit.items()) for hit in existing_hits}  # Create a set of frozensets for existing hits
        for hit in new_hits:
            hit_frozenset = frozenset(hit.items())
            if hit_frozenset not in seen:
                existing_hits.append(hit)
                seen.add(hit_frozenset)

    # Add primary matches
    for result in primary_matches:
        table_name = result.get("table_name")
        result_data = result.get("result_data")
        print(table_name,"build table name")
        print(result_data,"build result data")
        combined[table_name] = result_data

    # Add related data
    for related_index, related_hits in related_results.items():
        if related_index in combined:
            if related_hits:
                add_unique_hits(combined[related_index], related_hits)
        else:
            if related_hits:
                combined[related_index] = related_hits

    return combined


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
            relationship_with_other_index = tables[0].relationship_with_other_index
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
            table_name_to_relationships = {table.name: table.relationship_with_other_index for table in tables}
            table_id_to_display_name = {str(table.id): table.display_name for table in tables}

            print(table_id_to_display_name,"these are table id to display name")
            print(search_queries,"these are search queries")
            print(table_name_to_id,"these are table name to id")
            print(table_name_to_relationships,"table name to relationships")
            
            meiliresults = _execute_multi_search(search_queries, headers)
            # Create a deep copy of the original




            # # handle the relations
            # related_data = fetch_related_data(db,meiliresults,table_name_to_relationships,skip,limit)

            # print(meiliresults,"these are the meiliresults")
            # print(related_data,"these are related data")

            # new_meiliresults =  build_combined_results(meiliresults,related_data)

            # print(new_meiliresults,"these are meiliresults")

            # print(related_data,"this is the realated data")
            
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
                index_name = f"{sanitized_filename}"
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
    primary_key = "id"
    
    for i, record in enumerate(data):

        if "id" not in record:
            primary_key ="meili_id"

            record["meili_id"] = str(uuid.uuid4())
        for key,value in record.items():
            if isinstance(value,(datetime.datetime,datetime.date)):
                record[key] = value.isoformat()
            elif isinstance(value,(datetime.time)):
                record[key] = value.strftime('%H:%M:%S')
    
    crud.meilisearch.add_rows_to_index(
        index_name=table_name,
        rows=data,
        primary_key=primary_key
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




