#!/usr/bin/env python

import logging
import nf_core.schema
import jsonschema
from jsonschema.exceptions import ValidationError, SchemaError


def remove_required_fields(schema):
    """ Remove all required fields from a schema """
    if "required" in schema:
        schema.pop("required")
    for group_key, group in schema["definitions"].items():
        if "required" in group:
            schema["definitions"][group_key].pop("required")

    return schema


def schema_lint(self):
    """Pipeline schema syntax

    Pipelines should have a ``nextflow_schema.json`` file that describes the different
    pipeline parameters (eg. ``params.something``, ``--something``).

    .. tip:: Reminder: you should generally never need to edit this JSON file by hand.
             The ``nf-core schema build`` command can create *and edit* the file for you
             to keep it up to date, with a friendly user-interface for customisation.

    The lint test checks the schema for the following:

    * Schema should be a valid JSON file
    * Schema should adhere to `JSONSchema <https://json-schema.org/>`_, Draft 7.
    * Parameters can be described in two places:

        * As ``properties`` in the top-level schema object
        * As ``properties`` within subschemas listed in a top-level ``definitions`` objects

    * The schema must describe at least one parameter
    * There must be no duplicate parameter IDs across the schema and definition subschema
    * All subschema in ``definitions`` must be referenced in the top-level ``allOf`` key
    * The top-level ``allOf`` key must not describe any non-existent definitions
    * Core top-level schema attributes should exist and be set as follows:

        * ``$schema``: ``https://json-schema.org/draft-07/schema``
        * ``$id``: URL to the raw schema file, eg. ``https://raw.githubusercontent.com/YOURPIPELINE/master/nextflow_schema.json``
        * ``title``: ``YOURPIPELINE pipeline parameters``
        * ``description``: The pipeline config ``manifest.description``

    For example, an *extremely* minimal schema could look like this:

    .. code-block:: json

       {
         "$schema": "https://json-schema.org/draft-07/schema",
         "$id": "https://raw.githubusercontent.com/YOURPIPELINE/master/nextflow_schema.json",
         "title": "YOURPIPELINE pipeline parameters",
         "description": "This pipeline is for testing",
         "properties": {
           "first_param": { "type": "string" }
         },
         "definitions": {
           "my_first_group": {
             "properties": {
               "second_param": { "type": "string" }
             }
           }
         },
         "allOf": [{"$ref": "#/definitions/my_first_group"}]
       }

    .. tip:: You can check your pipeline schema without having to run the entire pipeline lint
             by running ``nf-core schema lint`` instead of ``nf-core lint``
    """
    passed = []
    warned = []
    failed = []

    # Only show error messages from schema
    logging.getLogger("nf_core.schema").setLevel(logging.ERROR)

    # Lint the schema
    self.schema_obj = nf_core.schema.PipelineSchema()
    self.schema_obj.get_schema_path(self.wf_path)

    try:
        self.schema_obj.load_lint_schema()
        # Validate default parameters, ignoring required ones as they might be empty
        schema_no_required = remove_required_fields(self.schema_obj.schema)
        jsonschema.validate(self.schema_obj.schema_defaults, schema_no_required)
        passed.append("Schema lint passed")
    except (ValidationError, SchemaError) as e:
        failed.append("Schema lint failed: {}".format(e))

    # Check the title and description - gives warnings instead of fail
    if self.schema_obj.schema is not None:
        try:
            self.schema_obj.validate_schema_title_description()
            passed.append("Schema title + description lint passed")
        except AssertionError as e:
            warned.append(str(e))

    return {"passed": passed, "warned": warned, "failed": failed}
