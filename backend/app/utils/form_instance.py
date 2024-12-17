from app import crud,schemas,models

def delete_form_instance(db,form_template_id):
    # get form instance
    form_instance = crud.form_instance.get_by_column_first(db=db,filter_column="template_id",filter_value=form_template_id)
    if form_instance:
        crud.form_instance.remove(db=db,db_obj=form_instance)



def generate_form_instance_from_form_template(form_template):
    template = form_template.template
    new_template = []

    # Iterate over each field in the template
    for field in template:
        print(field, "this is the field")
        
        # Dictionary to hold the mapped values for this field
        field_info = {
            "id": field.get("id")  # Start with the field_id
        }
        
        # Field mapping: maps target keys in the output to source keys in attributes
        field_mapping = {
            "title": "display_label",
            "info": "display_label",
            "placeholder": "placeholder",
            "element_type": "field_type",
            "value_type": "value_type",
        }

        # Iterate over each attribute in the 'elements' list
        for attribute in field.get("elements", []):
            for attr in attribute:  # Assuming each attribute is a dict
                attr_key = attr.get("name")  # Extract the title
                attr_value = attr.get("value")  # Extract the value

                 # If attr_value is a dictionary, extract the actual value
                if isinstance(attr_value, dict):
                    attr_value = attr_value.get("value")  # Extract 'value' key if exists
                
                # Match the field_mapping keys and populate field_info
                for target_key, source_key in field_mapping.items():
                    if attr_key == source_key:  # Check if the attribute matches a mapped source key
                        field_info[target_key] = attr_value
        
        # Append the gathered information to the new template
        new_template.append(field_info)

    return new_template





def create_or_update_form_instance(db,form_template):
    # check if form instance exists
    form_instance = crud.form_instance.get_by_column_first(db=db,filter_column="template_id",filter_value=form_template.id)
    if not form_instance:
        if form_template.name:
            print(form_template.id,form_template.owner_id)
            form_instance_template = generate_form_instance_from_form_template(form_template=form_template)
            # create the form instance
            form_instance_in = schemas.FormInstanceCreate(name=form_template.name,form=form_instance_template,template_id=form_template.id,owner_id=form_template.owner_id)
            form_instance = crud.form_instance.create(db=db,obj_in=form_instance_in)
    else:
        # update the form instance
        form_instance_template = generate_form_instance_from_form_template(form_template=form_template)
        form_instance_update_in = schemas.FormInstanceUpdate(name=form_template.name,form=form_instance_template)
        form_instance = crud.form_instance.update(db=db,db_obj=form_instance,obj_in=form_instance_update_in)


