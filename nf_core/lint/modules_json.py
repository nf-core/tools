#!/usr/bin/env python

from logging import warn
from nf_core.modules.modules_command import ModuleCommand


def modules_json(self):
    """Make sure all modules described in the ``modules.json`` file are actually installed

    Every module installed from ``nf-core/modules`` must have an entry in the ``modules.json`` file
    with an associated version git_sha hash.

    * Failure: If module entries are found in ``modules.json`` for modules that are not installed
    """
    passed = []
    warned = []
    failed = []

    # Load pipeline modules and modules.json
    modules_command = ModuleCommand(self.wf_path)
    modules_json = modules_command.load_modules_json()

    if modules_json:
        modules_command.get_pipeline_modules()

        all_modules_passed = True

        for repo in modules_json["repos"].keys():
            for key in modules_json["repos"][repo].keys():
                if not key in modules_command.module_names[repo]:
                    failed.append(f"Entry for `{key}` found in `modules.json` but module is not installed in pipeline.")
                    all_modules_passed = False

        if all_modules_passed:
            passed.append("Only installed modules found in `modules.json`")
    else:
        warned.append("Could not open `modules.json` file.")

    return {"passed": passed, "warned": warned, "failed": failed}
