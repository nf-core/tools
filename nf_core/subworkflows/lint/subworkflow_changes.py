"""
Check whether the content of a subworkflow has changed compared to the original repository
"""

from pathlib import Path

import nf_core.modules.modules_repo


def subworkflow_changes(subworkflow_lint_object, subworkflow):
    """
    Checks whether installed nf-core subworkflow have changed compared to the
    original repository

    Downloads the ``main.nf`` and ``meta.yml`` files for every subworkflow
    and compares them to the local copies

    If the subworkflow has a commit SHA entry in the ``modules.json``, the file content is
    compared against the files in the remote at this SHA.

    Only runs when linting a pipeline, not the modules repository
    """
    tempdir = subworkflow.component_dir
    subworkflow.branch = subworkflow_lint_object.modules_json.get_component_branch(
        "subworkflows", subworkflow.component_name, subworkflow.repo_url, subworkflow.org
    )
    modules_repo = nf_core.modules.modules_repo.ModulesRepo(remote_url=subworkflow.repo_url, branch=subworkflow.branch)

    for f, same in modules_repo.component_files_identical(
        subworkflow.component_name, tempdir, subworkflow.git_sha, "subworkflows"
    ).items():
        if same:
            subworkflow.passed.append(
                (
                    "check_local_copy",
                    "Local copy of subworkflow up to date",
                    f"{Path(subworkflow.component_dir, f)}",
                )
            )
        else:
            subworkflow.failed.append(
                (
                    "check_local_copy",
                    "Local copy of subworkflow does not match remote",
                    f"{Path(subworkflow.component_dir, f)}",
                )
            )
