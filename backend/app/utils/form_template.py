from uuid import uuid4
import requests
from app.core.security import settings
from fastapi import HTTPException
from requests.exceptions import RequestException
from app import crud,schemas
import json
def assign_uuids_to_template(template):
    if isinstance(template, list):
        for item in template:
            assign_uuids_to_template(item)
    elif isinstance(template, dict):
        if 'id' in template and template['id'] is None:
            template['id'] = str(uuid4())
        if 'uid' in template and template['uid'] is None:
            template['uid'] = str(uuid4())
        for value in template.values():
            if isinstance(value, (dict, list)):
                assign_uuids_to_template(value)

def fetch_aliases_for_column_name(db,column_name,form_template):
   
        extras = form_template.extras

        print(extras,"this is the extras")
        print(column_name,"this is the column name")
        if extras and extras.get(column_name):
            print("extras is there")
            url = "{0}/api/v1/db_scaled/search/{1}".format(settings.BACKEND_BASE_URL,extras.get(column_name))
    
            try:
                response = requests.get(url, headers={'accept': 'application/json'})
                response.raise_for_status()
                result = response.json()
                if result and result.get("column_aliases"):
                    return result.get("column_aliases")
                else:
                    return {"status":"pending"}

            except requests.exceptions.RequestException as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to generate SQL queries: {str(e)}"
                )
        else:
            # if not db_scaled_search_data_id it means we have to send a task to generate the synoyms and then save the db_scaled_search_data_id into extras
            print("no extras")

            try:
                data = {"column_name": column_name}
                url = f"{settings.BACKEND_BASE_URL}/api/v1/db_scaled/get_synonyms"
                headers = {
                    "accept": "application/json",
                    "Content-Type": "application/json"
                }
                # Send the POST request
                response = requests.post(url, headers=headers, json=data)

                # Check for HTTP errors
                response.raise_for_status()

                # Parse the JSON response
                result = response.json()
                print(result,"this is the result")
                if result:
                    extras = form_template.extras or {}
                    updated_extras = {**extras,column_name:result}
                    form_template_update_in = schemas.FormTemplateUpdate(extras=updated_extras)
                    form_template = crud.form_template.update(db=db,db_obj=form_template,obj_in=form_template_update_in)

                
                # Validate query_content exis

                return {"status": "pending"}

            except RequestException as e:
                # Handle request exceptions (e.g., connection error, timeout)
                raise HTTPException(status_code=400, detail="Failed to connect to the backend server.")
            except ValueError as e:
                # Handle JSON decoding errors
                raise HTTPException(status_code=500, detail="Invalid JSON response from the backend server.")
            except Exception as e:
                # Catch all other exceptions
                raise HTTPException(status_code=500, detail="An unexpected error occurred.")

# def parse_form_instance_data(form_instance_data, form_template_data):
#     extracted_data = []
#     print(form_instance_data,"this is the form_instance_data")
#     print(form_template_data,"this is the form template data")

#     # Create a dictionary for quick lookup of first_data by id
#     form_template_data_lookup = {item['id']: item for item in form_template_data}

#     # Iterate over form_data and extract corresponding data from first_data
#     for id,value in form_instance_data.items():
#         if id in form_template_data_lookup:
#             # Find aliases in the elements
#             aliases = []
#             for element_group in form_template_data_lookup[id]["elements"]:
#                 for element in element_group:
#                     if element.get("name") == "aliases":
#                         # Extract values from aliases
#                         aliases = [
#                             alias_item
#                             for alias_item in element.get("value", [])
#                         ]

#             # Append the extracted data
#             extracted_data.append({
#                 "id": id,
#                 "value": value,
#                 "aliases": aliases
#             })

#     return extracted_data

def parse_form_instance_data(form_instance_data, form_template_data):
    extracted_data = []

    print(form_instance_data,"this is the form_instance data")
    print(form_template_data,"this is the form tempalte")

    # Create a lookup dictionary for first_data by id
    form_template_data_lookup = {item["id"]: item for item in form_template_data}

    # Iterate through form_data
    for form_item in form_instance_data:
        form_data = form_item["data"]
        print(form_data,"new form data")  # Access the nested 'data' 
        print(type(form_data),"new form data type")
        form_data = json.loads(form_data)
        print(form_data,"newset form data",type(form_data))
        form_id = form_data["id"]
        if form_id in form_template_data_lookup:
            # Iterate through the elements of the corresponding first_data entry
            for element_group in form_template_data_lookup[form_id]["elements"]:
                for element in element_group:
                    if element.get("name") == "display_label":
                        display_label = element.get("value")
                        if display_label:
                            # Use display_label as the key and form_item's value
                            extracted_data.append({
                                "column": display_label,
                                "value": form_data["value"],
                                "exact_match": form_data["exact_match"]
                            })

                    # Extract aliases
                    if element.get("name") == "aliases":
                        aliases = element.get("value", [])
                        for alias_item in aliases:
                            alias_value = alias_item["value"]
                            if alias_value:
                                # Append dictionary with alias column, value, and exact_match
                                extracted_data.append({
                                    "column": alias_value,
                                    "value": form_data["value"],
                                    "exact_match": form_data["exact_match"]
                                })

    print(extracted_data,"extraced data is this")

    return extracted_data



