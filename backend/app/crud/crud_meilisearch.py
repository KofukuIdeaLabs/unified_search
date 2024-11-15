import os
from typing import List
from meilisearch import Client
from dotenv import load_dotenv
from app.core.config import settings

load_dotenv() 


class CrudMeilisearch:
    def __init__(self):
        self.master_key = settings.MEILI_MASTER_KEY
        self.url = "http://meilisearch:7700"
        self.client = Client(url=self.url, api_key=self.master_key)

    def get_keys(self):
        return self.client.get_keys()

    def get_index(self, index_name):
        return self.client.get_index(index_name)

    def create_index(self, index_name: str,primary_key="id"):
        print(index_name,primary_key,"this is the data")
        return self.client.create_index(index_name, {"primaryKey": primary_key})

    def check_status(self, task_uid: int):
        return self.client.get_task(task_uid)

    def failed_tasks(self, task_uids: list):
        return self.client.cancel_tasks({"uids": task_uids})

    def get_index_settings(self, index_name: str):
        return self.client.index(index_name).get_settings()

    def update_index_setting(self, index_name: str, settings: dict):
        return self.client.index(index_name).update_settings(body=settings).task_uid

    def update_filterable_settings(self, index_name: str, fields: list):
        return self.client.index(index_name).update_filterable_attributes(fields)

    def add_rows_to_index(self, index_name, rows: List[dict], primary_key="id"):
        return self.client.index(index_name).add_documents(rows, primary_key)

    def delete_row_from_index(self, index_name, row_primary_id):
        return (
            self.client.index(index_name)
            .delete_document(document_id=row_primary_id)
            .status
        )

    def search(
        self,
        index_name,
        search_query: str,
        filter_ids: list = [],
        filter_type: list = [],
    ):
        if index_name == "autocomplete":
            filter_queries = []
            if filter_ids:
                filter_queries.append(f"(id IN {filter_ids})")
            if filter_type:
                filter_queries.append(f"(unerth_object IN {filter_type})")

            filter_query = " AND ".join(filter_queries)

            # return filter_query

        if index_name == "document_chunks":
            filter_query = f"(doc_id IN {filter_ids})"

        return self.client.index(index_name).search(
            query=search_query,
            opt_params={"limit": 10},
        )["hits"]

    def search_batch(
        self,
        index_name,
        search_queries: list,
        limit=20,
    ):
        # Right now supporting only knowledge bank
        search_queries = [
            {
                "indexUid": index_name,
                "q": term,
                "limit": limit,
                "showRankingScore": True,
            }
            for term in search_queries
        ]
        meiliresults = self.client.multi_search(queries=search_queries)
        # print(meiliresults)
        results = []
        for i, ele in enumerate(meiliresults["results"]):
            inner_results = []
            # print(ele.keys())
            for result in ele["hits"]:
                inner_results.append(
                    {
                        "doc_id": result["doc_id"],
                        "id": result["id"].split("_")[0],
                        "score": result["_rankingScore"],
                    }
                )
            results.append(inner_results)
        return results

    def update_entity_name(self, index_name: str, id, new_entity_name: str):
        return self.client.index(index_name).update_documents(
            [{"id": id, "entity": new_entity_name}]
        )


meilisearch = CrudMeilisearch()


