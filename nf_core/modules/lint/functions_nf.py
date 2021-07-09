#!/usr/bin/env python
import logging
import os
import nf_core

log = logging.getLogger(__name__)


def functions_nf(module_lint_object, module):
    """
    Lint a functions.nf file
    Verifies that the file exists and contains all necessary functions
    """
    local_copy = None
    template_copy = None
    try:
        with open(module.function_nf, "r") as fh:
            lines = fh.readlines()
        module.passed.append(("functions_nf_exists", "'functions.nf' exists", module.function_nf))
    except FileNotFoundError as e:
        module.failed.append(("functions_nf_exists", "'functions.nf' does not exist", module.function_nf))
        return

    # Test whether all required functions are present
    required_functions = ["getSoftwareName", "initOptions", "getPathFromList", "saveFiles"]
    lines = "\n".join(lines)
    contains_all_functions = True
    for f in required_functions:
        if not "def " + f in lines:
            module.failed.append(("functions_nf_func_exist", "Function is missing: `{f}`", module.function_nf))
            contains_all_functions = False
    if contains_all_functions:
        module.passed.append(("functions_nf_func_exist", "All functions present", module.function_nf))

    # Compare functions.nf file to the most recent template
    # Get file content of the module functions.nf
    try:
        local_copy = open(module.function_nf, "r").read()
    except FileNotFoundError as e:
        log.error(f"Could not open {module.function_nf}")

    # Get the template file
    template_copy_path = os.path.join(os.path.dirname(nf_core.__file__), "module-template/modules/functions.nf")
    try:
        template_copy = open(template_copy_path, "r").read()
    except FileNotFoundError as e:
        log.error(f"Could not open {template_copy_path}")

    # Compare the files
    if local_copy and template_copy:
        if local_copy != template_copy:
            module.failed.append(
                ("function_nf_comparison", "New version of functions.nf available", module.function_nf)
            )
        else:
            module.passed.append(("function_nf_comparison", "functions.nf is up to date", module.function_nf))
