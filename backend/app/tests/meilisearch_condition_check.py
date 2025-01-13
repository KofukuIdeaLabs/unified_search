from meilisearch import Client

# Initialize Meilisearch client
client = Client('http://meilisearch:7700', 'f9987e1e-b43c-4346-b5c5-2a7e442b80d')  # Update with your Meilisearch URL and API key

# Define the Meilisearch queries
queries = [

    {

        "indexUid": "aircel",

        "q": "ASHOK",

        "attributesToSearchOn": [

            "name_of_point_of_sale"

        ],

        "limit": 50,

        "offset": 0,

        "filter": "phone_no = '9804820830' AND alt_phone = '9804820830'"

    },

    {

        "indexUid": "aircel",

        "q": "ASHOK",

        "attributesToSearchOn": [

            "first_name"

        ],

        "limit": 50,

        "offset": 0,

        "filter": "phone_no = '9804820830' AND alt_phone = '9804820830'"

    },

    {

        "indexUid": "aircel",

        "q": "LT KAILASH",

        "attributesToSearchOn": [

            "fathers_first_name"

        ],

        "limit": 50,

        "offset": 0,

        "filter": "phone_no = '9804820830' AND alt_phone = '9804820830'"

    },

    {

        "indexUid": "aircel",

        "q": "LT KAILASH",

        "attributesToSearchOn": [

            "fathers_last_name"

        ],

        "limit": 50,

        "offset": 0,

        "filter": "phone_no = '9804820830' AND alt_phone = '9804820830'"

    },

    {

        "indexUid": "aircel",

        "q": "44C BAGHBAZAR",

        "attributesToSearchOn": [

            "address_1"

        ],

        "limit": 50,

        "offset": 0,

        "filter": "phone_no = '9804820830' AND alt_phone = '9804820830'"

    },

    {

        "indexUid": "airtel",

        "q": "ASHOK",

        "attributesToSearchOn": [

            "name_of_point_of_sale"

        ],

        "limit": 50,

        "offset": 0,

        "filter": "phone_no = '9804820830' AND alt_phone = '9804820830'"

    },

    {

        "indexUid": "airtel",

        "q": "ASHOK",

        "attributesToSearchOn": [

            "first_name"

        ],

        "limit": 50,

        "offset": 0,

        "filter": "phone_no = '9804820830' AND alt_phone = '9804820830'"

    },

    {

        "indexUid": "airtel",

        "q": "LT KAILASH",

        "attributesToSearchOn": [

            "fathers_first_name"

        ],

        "limit": 50,

        "offset": 0,

        "filter": "phone_no = '9804820830' AND alt_phone = '9804820830'"

    },

    {

        "indexUid": "airtel",

        "q": "LT KAILASH",

        "attributesToSearchOn": [

            "fathers_last_name"

        ],

        "limit": 50,

        "offset": 0,

        "filter": "phone_no = '9804820830' AND alt_phone = '9804820830'"

    },

    {

        "indexUid": "airtel",

        "q": "44C BAGHBAZAR",

        "attributesToSearchOn": [

            "address_1"

        ],

        "limit": 50,

        "offset": 0,

        "filter": "phone_no = '9804820830' AND alt_phone = '9804820830'"

    }

]

def search_query(client, query):
    try:
        index = client.index(query["indexUid"])
        results = index.search(query["q"], {
            # "filter": query["filters"],
            # "limit": query["limit"]
        })
        print(f"Results for index '{query['indexUid']}': {results['hits']}")
    except Exception as e:
        if "index not found" in str(e).lower():  # Check for index not found error
            print(f"Index '{query['index']}' not found. Please check the index name.")
        else:
            print(f"Error for index '{query['indexUid']}': {e}")

# Execute each query
for query in queries:
    search_query(client, query)