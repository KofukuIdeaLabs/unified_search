from meilisearch import Client

# Initialize Meilisearch client
client = Client('http://192.168.128.2:7700', 'f9987e1e-b43c-4346-b5c5-2a7e442b80d')  # Update with your Meilisearch URL and API key

# Define the Meilisearch queries
queries = [{'q': 'CHIRAG', 'filters': None, 'index': 'kp_employee'}, {'q': 'CHIRAG', 'filters': None, 'index': 'fmh_bar_data'}, {'q': 'CHIRAG', 'filters': None, 'index': 'idea'}, {'q': 'CHIRAG', 'filters': None, 'index': 'jail_cases'}, {'q': 'CHIRAG', 'filters': None, 'index': 'jail_genquery'}, {'q': 'CHIRAG', 'filters': None, 'index': 'jail_prisonerdetails'}, {'q': 'CHIRAG', 'filters': None, 'index': 'jail_terroristlist'}, {'q': 'CHIRAG', 'filters': None, 'index': 'jail_vadocourtcases'}, {'q': 'CHIRAG', 'filters': None, 'index': 'ttcriminal'}, {'q': 'CHIRAG', 'filters': None, 'index': 'ttcriminal'}, {'q': 'CHIRAG', 'filters': None, 'index': 'vehcl_data'}, {'q': 'CHIRAG', 'filters': None, 'index': 'kp_employee'}]

def search_query(client, query):
    try:
        index = client.index(query["index"])
        results = index.search(query["q"], {
            "filter": query["filters"],
            # "limit": query["limit"]
        })
        print(f"Results for index '{query['index']}': {results['hits']}")
    except Exception as e:
        if "index not found" in str(e).lower():  # Check for index not found error
            print(f"Index '{query['index']}' not found. Please check the index name.")
        else:
            print(f"Error for index '{query['index']}': {e}")

# Execute each query
for query in queries:
    search_query(client, query)