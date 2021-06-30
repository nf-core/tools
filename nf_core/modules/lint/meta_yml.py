#!/usr/bin/env python

from operator import imod


import yaml


def meta_yml(module_lint_object, module):
    """Lint a meta yml file"""
    required_keys = ["name", "input", "output"]
    required_keys_lists = ["input", "output"]
    try:
        with open(module.meta_yml, "r") as fh:
            meta_yaml = yaml.safe_load(fh)
        module.passed.append(("meta_yml_exists", "Module `meta.yml` exists", module.meta_yml))
    except FileNotFoundError:
        module.failed.append(("meta_yml_exists", "Module `meta.yml` does not exist", module.meta_yml))
        return

    # Confirm that all required keys are given
    contains_required_keys = True
    all_list_children = True
    for rk in required_keys:
        if not rk in meta_yaml.keys():
            module.failed.append(("meta_required_keys", f"`{rk}` not specified", module.meta_yml))
            contains_required_keys = False
        elif not isinstance(meta_yaml[rk], list) and rk in required_keys_lists:
            module.failed.append(("meta_required_keys", f"`{rk}` is not a list", module.meta_yml))
            all_list_children = False
    if contains_required_keys:
        module.passed.append(("meta_required_keys", "`meta.yml` contains all required keys", module.meta_yml))

    # Confirm that all input and output channels are specified
    if contains_required_keys and all_list_children:
        meta_input = [list(x.keys())[0] for x in meta_yaml["input"]]
        for input in module.inputs:
            if input in meta_input:
                module.passed.append(("meta_input", f"`{input}` specified", module.meta_yml))
            else:
                module.failed.append(("meta_input", f"`{input}` missing in `meta.yml`", module.meta_yml))

        meta_output = [list(x.keys())[0] for x in meta_yaml["output"]]
        for output in module.outputs:
            if output in meta_output:
                module.passed.append(("meta_output", "`{output}` specified", module.meta_yml))
            else:
                module.failed.append(("meta_output", "`{output}` missing in `meta.yml`", module.meta_yml))

        # confirm that the name matches the process name in main.nf
        if meta_yaml["name"].upper() == module.process_name:
            module.passed.append(("meta_name", "Correct name specified in `meta.yml`", module.meta_yml))
        else:
            module.failed.append(
                ("meta_name", "Conflicting process name between `meta.yml` and `main.nf`", module.meta_yml)
            )
