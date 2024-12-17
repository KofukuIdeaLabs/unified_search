from uuid import uuid4
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