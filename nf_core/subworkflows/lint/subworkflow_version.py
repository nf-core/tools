"""
Verify that a subworkflow has a correct entry in the modules.json file
"""

import logging
from pathlib import Path

from git.exc import GitCommandError

from nf_core.modules.modules_repo import ModulesRepoUnavailableError

log = logging.getLogger(__name__)


def subworkflow_version(subworkflow_lint_object, subworkflow):
    """
    Verifies that the subworkflow has a version specified in the ``modules.json`` file

    It checks whether the subworkflow has an entry in the ``modules.json`` file
    containing a commit SHA. If that is true, it verifies that there are no
    newer version of the subworkflow available.

    The following checks are performed:

    git_sha
    ^^^^^^^

    The subworkflow must have a ``git_sha`` entry in ``modules.json``.

    subworkflow_version
    ^^^^^^^^^^^^^^^^^^^

    The subworkflow version must match the latest commit
    in the remote repository. A warning is issued if a newer version is available.
    """

    modules_json_path = Path(subworkflow_lint_object.directory, "modules.json")
    # Verify that a git_sha exists in the `modules.json` file for this module
    version = subworkflow_lint_object.modules_json.get_subworkflow_version(
        subworkflow.component_name, subworkflow.repo_url, subworkflow.org
    )
    if version is None:
        subworkflow.failed.append(
            ("subworkflow_version", "git_sha", "No git_sha entry in `modules.json`", modules_json_path)
        )
        return

    subworkflow.git_sha = version
    subworkflow.passed.append(
        ("subworkflow_version", "git_sha", "Found git_sha entry in `modules.json`", modules_json_path)
    )

    subworkflow.branch = subworkflow_lint_object.modules_json.get_component_branch(
        "subworkflows", subworkflow.component_name, subworkflow.repo_url, subworkflow.org
    )
    try:
        modules_repo = subworkflow_lint_object.get_lint_repo(subworkflow.repo_url, subworkflow.branch)
        latest = next(iter(modules_repo.get_component_git_log(subworkflow.component_name, "subworkflows")), None)
    except (ModulesRepoUnavailableError, GitCommandError, UserWarning) as e:
        subworkflow.warned.append(
            (
                "subworkflow_version",
                "subworkflow_version",
                f"Could not check subworkflow version: {e}",
                subworkflow.component_dir,
            )
        )
        return

    if latest is None:
        subworkflow.warned.append(
            (
                "subworkflow_version",
                "subworkflow_version",
                "No git history found for subworkflow",
                subworkflow.component_dir,
            )
        )
    elif version == latest["git_sha"]:
        message = (
            "Subworkflow matches the cached version"
            if subworkflow_lint_object.no_pull
            else "Subworkflow is in the latest version"
        )
        subworkflow.passed.append(("subworkflow_version", "subworkflow_version", message, subworkflow.component_dir))
    else:
        subworkflow.warned.append(
            ("subworkflow_version", "subworkflow_version", "New version available", subworkflow.component_dir)
        )
