from app.prompts.meta_data_generation import GENERATE_TABLE_SYNONYMS, GENERATE_COLUMN_SYNONYMS, GENERATE_TABLE_DESCRIPTION, GENERATE_COLUMN_DESCRIPTION
from app.utils.llm import process_llm_request_openai
from app.schemas.index_data import TableSynonyms, ColumnSynonyms, TableDescription, ColumnDescription

class IndexData:
    def __init__(self):
        pass


    

    def generate_table_synonyms(self,table_name, column_names, data):
        print(table_name, column_names, data)
        system_prompt = GENERATE_TABLE_SYNONYMS
        user_prompt = f"table name: {table_name}, column names: {column_names}, data: {data}"
        table_synonyms = process_llm_request_openai(model="gpt-4o-mini", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], response_schema=TableSynonyms)
        print(table_synonyms.table_synonyms,"this is the table synonyms")
        return table_synonyms

    def generate_table_description(self,table_name, column_names, data):
        system_prompt = GENERATE_TABLE_DESCRIPTION
        user_prompt = f"table name: {table_name}, column names: {column_names}, data: {data}"
        table_description = process_llm_request_openai(model="gpt-4o-mini", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], response_schema=TableDescription)
        print(table_description)
        return table_description

    def generate_column_synonyms(self,table_name, column_name, data):
        system_prompt = GENERATE_COLUMN_SYNONYMS
        user_prompt = f"table name: {table_name}, column name: {column_name}, data: {data}"
        column_synonyms = process_llm_request_openai(model="gpt-4o-mini", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], response_schema=ColumnSynonyms)
        print(column_synonyms)
        return column_synonyms

    def generate_column_description(self,table_name, column_name, data):
        system_prompt = GENERATE_COLUMN_DESCRIPTION
        user_prompt = f"table name: {table_name}, column name: {column_name}, data: {data}"
        column_description = process_llm_request_openai(model="gpt-4o-mini", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], response_schema=ColumnDescription)
        print(column_description)
        return column_description
        
        
index_data = IndexData()