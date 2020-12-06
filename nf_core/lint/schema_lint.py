#!/usr/bin/env python

import logging
import nf_core.schema


def schema_lint(self):
    """ Lint the pipeline schema """
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
        passed.append("Schema lint passed")
    except AssertionError as e:
        failed.append("Schema lint failed: {}".format(e))

    # Check the title and description - gives warnings instead of fail
    if self.schema_obj.schema is not None:
        try:
            self.schema_obj.validate_schema_title_description()
            passed.append("Schema title + description lint passed")
        except AssertionError as e:
            warned.append(e)

    return {"passed": passed, "warned": warned, "failed": failed}
