def get_class_attributes(classObj):
    print("[class attributes]")
    attributes = []
    attribute_values = []
    for attribute in classObj.__dict__.keys():
        if attribute[:2] != "__":
            value = getattr(classObj, attribute)
            if not callable(value):
                attributes.append(attribute)
                attribute_values.append(value)
    return (attribute, attribute_values)