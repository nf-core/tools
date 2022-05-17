#!/usr/bin/env python


import yaml


def meta_yml(module_lint_object, module):
    """
    Lint a ``meta.yml`` file

    The lint test checks that the module has
    a ``meta.yml`` file and that it contains
    the required keys: ``name``, input`` and
    ``output``.

    In addition it checks that the module name
    and module input is consistent between the
    ``meta.yml`` and the ``main.nf``.

    """
    required_keys = ["name", "output"]
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
            module.failed.append(("meta_required_keys", f"`{rk}` not specified in YAML", module.meta_yml))
            contains_required_keys = False
        elif rk in meta_yaml.keys() and not isinstance(meta_yaml[rk], list) and rk in required_keys_lists:
            module.failed.append(("meta_required_keys", f"`{rk}` is not a list", module.meta_yml))
            all_list_children = False
    if contains_required_keys:
        module.passed.append(("meta_required_keys", "`meta.yml` contains all required keys", module.meta_yml))

    # Confirm that all input and output channels are specified
    if contains_required_keys and all_list_children:
        if "input" in meta_yaml:
            meta_input = [list(x.keys())[0] for x in meta_yaml["input"]]
            for input in module.inputs:
                if input in meta_input:
                    module.passed.append(("meta_input", f"`{input}` specified", module.meta_yml))
                else:
                    module.failed.append(("meta_input", f"`{input}` missing in `meta.yml`", module.meta_yml))

        if "output" in meta_yaml:
            meta_output = [list(x.keys())[0] for x in meta_yaml["output"]]
            for output in module.outputs:
                if output in meta_output:
                    module.passed.append(("meta_output", f"`{output}` specified", module.meta_yml))
                else:
                    module.failed.append(("meta_output", f"`{output}` missing in `meta.yml`", module.meta_yml))

        # confirm that the name matches the process name in main.nf
        if meta_yaml["name"].upper() == module.process_name:
            module.passed.append(("meta_name", "Correct name specified in `meta.yml`", module.meta_yml))
        else:
            module.failed.append(
                (
                    "meta_name",
                    f"Conflicting process name between meta.yml (`{meta_yaml['name']}`) and main.nf (`{module.process_name}`)",
                    module.meta_yml,
                )
            )
