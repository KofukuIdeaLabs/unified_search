import meilisearch

# Meilisearch client initializations
source_meili_client = meilisearch.Client('http://127.0.0.1:7700', 'your_source_meilisearch_api_key')
destination_meili_client = meilisearch.Client('http://127.0.0.1:7701', 'your_destination_meilisearch_api_key')

def copy_index_data(index_name):
    """Copy data from a Meilisearch index on one service to another."""
    # Fetch data from the source index
    source_index = source_meili_client.index(index_name)
    documents = source_index.get_documents()
    
    if documents:
        # Index data to the destination Meilisearch
        destination_index = destination_meili_client.index(index_name)
        response = destination_index.add_documents(documents)
        print("Copy response:", response)
        print(f"Successfully copied {len(documents)} documents to the destination Meilisearch.")
    else:
        print("No documents found to copy.")

if __name__ == "__main__":
    # Specify the index to copy
    index_name = 'your_index_name'
    copy_index_data(index_name)
