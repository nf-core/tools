#!/usr/bin/env python

import nf_core.schema


def schema_description(self):
    """Check that every parameter in the schema has a description

    The ``nextflow_schema.json`` pipeline schema should describe every flat parameter
    Furthermore warns about parameters outside of groups

    * Warning: Parameters in ``nextflow_schema.json`` without a description
    * Warning: Parameters in ``nextflow_schema.json`` that are defined outside of a group
    """
    passed = []
    warned = []
    ignored = []

    # First, get the top-level config options for the pipeline
    # Schema object already created in the `schema_lint` test
    self.schema_obj = nf_core.schema.PipelineSchema()
    self.schema_obj.get_schema_path(self.wf_path)
    self.schema_obj.get_wf_params()
    self.schema_obj.no_prompts = True
    self.schema_obj.load_lint_schema()

    # Get parameters that should be ignored according to the linting config
    ignore_params = self.lint_config.get("schema_description", [])

    # Get ungrouped params
    if "properties" in self.schema_obj.schema.keys():
        ungrouped_params = self.schema_obj.schema["properties"].keys()
        for up in ungrouped_params:
            if up in ignore_params:
                ignored.append(f"Ignored ungrouped param in schema: `{up}`")
            else:
                warned.append(f"Ungrouped param in schema: `{up}`")

    # Iterate over groups and add warning for parameters without a description
    for group_key in self.schema_obj.schema["definitions"].keys():
        group = self.schema_obj.schema["definitions"][group_key]
        for param_key, param in group["properties"].items():
            if param_key in ignore_params:
                ignored.append(f"Ignoring description check for param in schema: `{param_key}`")
                continue
            if "description" not in param.keys():
                warned.append(f"No description provided in schema for parameter: `{param_key}`")

    for ip in ignore_params:
        ignored.append(f"Parameter is ignored: `{ip}`")

    return {"passed": passed, "warned": warned, "ignored": ignored}
