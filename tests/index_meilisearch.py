import mysql.connector
import meilisearch

# MySQL Database connection details
mysql_config = {
    'host': 'your_mysql_host',
    'user': 'your_mysql_user',
    'password': 'your_mysql_password',
    'database': 'your_mysql_db'
}

# Meilisearch client initialization
meili_client = meilisearch.Client('http://127.0.0.1:7700', 'your_meilisearch_api_key')
index_name = 'your_index_name'

def fetch_data_from_mysql(query):
    """Fetch data from MySQL database based on the query provided."""
    connection = mysql.connector.connect(**mysql_config)
    cursor = connection.cursor(dictionary=True)
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    return results

def index_data_to_meilisearch(index_name, documents):
    """Index the given data into Meilisearch."""
    index = meili_client.index(index_name)
    response = index.add_documents(documents)
    print("Indexing response:", response)

if __name__ == "__main__":
    # Sample SQL query (customize as needed)
    query = "SELECT id, name, description FROM your_table_name;"
    
    # Fetch data from MySQL
    data = fetch_data_from_mysql(query)

    if data:
        # Index data to Meilisearch
        index_data_to_meilisearch(index_name, data)
        print(f"Successfully indexed {len(data)} records to Meilisearch.")
    else:
        print("No data found to index.")
