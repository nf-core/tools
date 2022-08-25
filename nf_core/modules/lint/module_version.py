#!/usr/bin/env python
"""
Verify that a module has a correct entry in the modules.json file
"""

import logging
from pathlib import Path

import nf_core
import nf_core.modules.module_utils
import nf_core.modules.modules_repo

log = logging.getLogger(__name__)


def module_version(module_lint_object, module):
    """
    Verifies that the module has a version specified in the ``modules.json`` file

    It checks whether the module has an entry in the ``modules.json`` file
    containing a commit SHA. If that is true, it verifies that there are no
    newer version of the module available.
    """

    modules_json_path = Path(module_lint_object.dir, "modules.json")

    # Verify that a git_sha exists in the `modules.json` file for this module
    version = module_lint_object.modules_json.get_module_version(
        module.module_name, module_lint_object.modules_repo.fullname
    )
    if version is None:
        module.failed.append(("git_sha", "No git_sha entry in `modules.json`", modules_json_path))
        return

    module.git_sha = version
    module.passed.append(("git_sha", "Found git_sha entry in `modules.json`", modules_json_path))

    # Check whether a new version is available
    try:
        modules_repo = nf_core.modules.modules_repo.ModulesRepo()
        module_git_log = modules_repo.get_module_git_log(module.module_name)
        if version == next(module_git_log)["git_sha"]:
            module.passed.append(("module_version", "Module is the latest version", module.module_dir))
        else:
            module.warned.append(("module_version", "New version available", module.module_dir))
    except UserWarning:
        module.warned.append(("module_version", "Failed to fetch git log", module.module_dir))
