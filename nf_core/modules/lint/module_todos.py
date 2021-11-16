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
    module.wf_path = module.module_dir
    results = pipeline_todos(module)
    for i, warning in enumerate(results["warned"]):
        module.warned.append(("module_todo", warning, results["file_paths"][i]))
