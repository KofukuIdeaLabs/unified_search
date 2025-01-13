from meilisearch import Client

# Initialize Meilisearch client
client = Client('http://192.168.128.2:7700', 'f9987e1e-b43c-4346-b5c5-2a7e442b80d')  # Update with your Meilisearch URL and API key

# Define the provided data
data = [
    "Name_2:CHIRAG OR City:CHIRAG",
    "provider:CHIRAG",
    "name:CHIRAG",
    "email:CHIRAG",
    "jail_name:CHIRAG",
    "field_name:CHIRAG",
    "Prisoner_Name:CHIRAG",
    "PID_No:CHIRAG",
    "FAMILY_ID:CHIRAG",
    "Azimuth:CHIRAG OR MSCName:CHIRAG OR MCC:CHIRAG",
    "date_of_upload:CHIRAG",
    "mcc:CHIRAG",
    "FACE:CHIRAG OR ACTS4:CHIRAG OR PHOTONO:CHIRAG",
    "CL_DESC:CHIRAG"
]

# Function to convert the conditions into Meilisearch queries
def process_condition(condition):
    # Remove parentheses and split on OR
    condition = condition.strip("()")
    fields = condition.split(" OR ")
    
    # Build Meilisearch search syntax
    query = " OR ".join([field.replace("=", ":").replace("*", "").strip() for field in fields])
    return query

def search_in_index(index_name, condition):
    meilisearch_query = process_condition(condition)
    print(f"Searching in index '{index_name}' with query: {meilisearch_query}")
    results = client.index(index_name).search(meilisearch_query)  # Search in the current index
    print(f"Results: {results['hits']}")

# Retrieve all indexes
indexes = client.get_indexes()  # Retrieve all indexes

# Process conditions and perform searches across all indexes
for condition in data:
    # Using a list comprehension to search in all indexes for each condition
    [search_in_index(index.uid, condition) for index in indexes['results']]  # Search in all indexes for each condition

