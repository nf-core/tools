if link.startswith("https://github.com/nf-core/tools/blob/main/nf_core/"):
    # Reconstruct the module path reliably.
    # Preserve existing '/' separators and replace only
    # underscore separators that belong to a single path
    # component. This works for both flat and nested names.
    name_parts = name.lower().split("/")
    new_parts = []
    for part in name_parts:
        subparts = part.split("_")
        new_parts.append("/".join(subparts))
    component_name = "/".join(new_parts)
    component_dict: dict[str, str] = {"name": component_name}
    modules[component_name] = component_dict
elif link.startswith("../"):
    component_name = name.lower()
    component_dict = {"name": component_name}
    subworkflows[component_name] = component_dict