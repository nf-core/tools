#!/usr/bin/env python
import logging
from nf_core.lint.pipeline_todos import pipeline_todos

log = logging.getLogger(__name__)


def module_todos(module_lint_object, module):
    """
    Look for TODO statements in the module files
    Slight modification of the "nf_core.lint.pipeline_todos" function to make it work
    for a single module
    """

    # Main module directory
    mod_results = pipeline_todos(None, root_dir=module.module_dir)
    for i, warning in enumerate(mod_results["warned"]):
        module.warned.append(("module_todo", warning, mod_results["file_paths"][i]))
    for i, passed in enumerate(mod_results["passed"]):
        module.passed.append(("module_todo", passed, module.module_dir))

    # Module tests directory
    test_results = pipeline_todos(None, root_dir=module.test_dir)
    for i, warning in enumerate(test_results["warned"]):
        module.warned.append(("module_todo", warning, test_results["file_paths"][i]))
    for i, passed in enumerate(test_results["passed"]):
        module.passed.append(("module_todo", passed, module.test_dir))
