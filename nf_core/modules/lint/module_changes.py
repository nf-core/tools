"""
Check whether the content of a module has changed compared to the original repository
"""
import os

import requests
import rich


def module_changes(module_lint_object, module):
    """
    Checks whether installed nf-core modules have changed compared to the
    original repository

    Downloads the ``main.nf`` and ``meta.yml`` files for every module
    and compares them to the local copies

    If the module has a commit SHA entry in the ``modules.json``, the file content is
    compared against the files in the remote at this SHA.

    Only runs when linting a pipeline, not the modules repository
    """
    for f, same in module_lint_object.modules_repo.module_files_identical(
        module.module_name, module.module_dir, module.git_sha
    ).items():
        if same:
            module.passed.append(
                (
                    "check_local_copy",
                    "Local copy of module up to date",
                    f"{os.path.join(module.module_dir, f)}",
                )
            )
        else:
            module.failed.append(
                (
                    "check_local_copy",
                    "Local copy of module does not match remote",
                    f"{os.path.join(module.module_dir, f)}",
                )
            )
