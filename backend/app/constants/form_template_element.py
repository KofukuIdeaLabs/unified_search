class FormTemplateElement:
    FIELD_GROUP = {
        "name": "field_group",
        "template": {
            "id": None,
            "is_saved":False,
            "elements": [
                [
                    {
                        "id": None,
                        "hint": None,
                        "info": "this is the info",
                        "title": "name of the field",
                        "value": None,
                        "required": False,
                        "element_type": "heading_3",
                        "name":"title"
                    },
                    {
                        "id": None,
                        "hint": None,
                        "info": "this is the info",
                        "title": "Relevance",
                        "value": None,
                        "required": False,
                        "element_type": "toggle",
                        "name":"relevance"
                    },
                ],[
                    {
                        "id": None,
                        "hint": "enter display label",
                        "info": "this is the info",
                        "title": "Display Label",
                        "required": True,
                        "element_type": "text_input",
                        "name":"display_label",
                        "value": None,

                    },
                    {
                        "id": None,
                        "hint": "enter place holder text",
                        "info": "this is the info",
                        "title": "Place Holder Text",
                        "required": True,
                        "element_type": "text_input",
                        "name":"placeholder",
                        "value": None,
                    },
                ],
                [
                    {
                        "id": None,
                        "hint": None,
                        "info": None,
                        "title": None,
                        "required": False,
                        "element_type": "horizontal_rule",
                        "name":"horizontal_rule",
                        "value": None,
                    },
                ],
                [
                    {
                        "id": None,
                        "hint": "select Field Type",
                        "info": "this is the info",
                        "title": "Field Type",
                        "required": True,
                        "element_type": "drop_down",
                        "name":"field_type",
                        "value": None,
                    },
                    {
                        "id": None,
                        "hint": "select value type",
                        "info": "this is the info",
                        "title": "Value Type",
                        "required": True,
                        "element_type": "drop_down",
                        "name":"value_type",
                        "value": None,
                    },
                ],
                [
                    {
                        "id": None,
                        "hint": "enter alternate names or terms separated by comma",
                        "info": "this is the info",
                        "title": "Aliases",
                        "required": True,
                        "element_type": "multiple_selector",
                        "name":"aliases",
                        "value": None,
                    }
                ],
            ],
        },
    }
