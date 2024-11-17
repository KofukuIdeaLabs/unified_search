from .celery import app
from app.api import deps
import time
from app import crud, schemas,models
import sqlparse
from sqlparse.sql import Identifier, IdentifierList
from sqlparse.tokens import Keyword, DML
from sqlalchemy import text

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





