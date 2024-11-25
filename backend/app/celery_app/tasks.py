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
        # Simulate a time-consuming SQL task
        print(f"Task {search_result_id}: Running query: {query}")
        print(type(query),"this is the type of query")
        # Execute SQL queries and collect results
        results = []
        for sql in query:
            # Extract table name from query (assumes format "SELECT * FROM table_name WHERE...")
            # Execute query and get results
            print(sql,"this is the sql query")
            query_result = [dict(row._mapping) for row in db.execute(text(sql)).fetchall()]
            print(query_result,"this is the query result")
            # Add to results in specified format
            results.append({
                "table_name": extract_table_names(sql),
                "result_data": query_result
            })
        # run the sql query
        # once the query is run, update the search result with the query result

        print(results,"this is the results")
      
        search_result = crud.search_result.get(db=db, id=search_result_id)
        search_result_update_in = schemas.SearchResultUpdate(result=results)
        search_result = crud.search_result.update(db=db,db_obj=search_result,obj_in=search_result_update_in)
        return True
    except Exception as e:
        print(e,"this is the error")
        raise self.retry(exc=e)

@app.task(bind=True, max_retries=3)
def index_data_file(self, db_id: str, saved_files: List[dict]):
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
                    data = df.to_dict(orient='records')
                    # extract the table name from the filename
                    table_name = filename.split(".")[0]
                    # check if the table already exists

                    table = crud.indexed_table.get_table_by_name_and_db_id(db=db,name=table_name,db_id=db_id)
                    if not table:
                        # create table from the name of the file
                        table = crud.indexed_table.create(db=db,obj_in=schemas.IndexedTableCreate(name=table_name,db_id=db_id))
                    # index into the meilisearch
                    # generate the unique id for each row
                    unique_ids = [str(uuid.uuid4()) for _ in range(len(data))]
                    # add the unique ids to the data
                    for i in range(len(data)):
                        data[i]["id"] = unique_ids[i]
                    print(data,"this is the data for the csv file")
                    crud.meilisearch.add_rows_to_index(index_name=table_name,rows=data,primary_key="id")
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
        raise self.retry(exc=e)




