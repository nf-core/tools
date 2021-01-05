#!/usr/bin/env python

import logging
import yaml
import json
import jsonschema
import os
import requests


def actions_schema_validation(self):
    """
    Validate workflows against a schema

    Uses the JSON Schema from
    https://json.schemastore.org/github-workflow
    to verify that all workflow yml files adhere to the correct Schema
    """
    passed = []
    warned = []
    failed = []

    # Only show error messages from schema
    logging.getLogger("nf_core.schema").setLevel(logging.ERROR)

    # Get all workflow files
    action_workflows = os.listdir(os.path.join(self.wf_path, ".github/workflows"))

    # Load the GitHub workflow schema
    r = requests.get("https://json.schemastore.org/github-workflow", allow_redirects=True)
    schema = r.json()
    # Validate all workflows against the schema
    for wf in action_workflows:
        # load workflow
        wf_path = os.path.join(self.wf_path, ".github/workflows", wf)
        with open(wf_path, "r") as fh:
            wf_json = yaml.safe_load(fh)

        try:
            # fix yaml parsing on as True
            wf_json["on"] = wf_json.pop(True)
        except Exception as e:
            failed.append("Missing 'on' keyword in {}.format(wf)")

        # Validate the workflow
        try:
            jsonschema.validate(wf_json, schema)
            passed.append("Workflow validation passed: {}".format(wf))
        except Exception as e:
            failed.append("Workflow validation failed for {}: {}".format(wf, e))

    return {"passed": passed, "warned": warned, "failed": failed}
