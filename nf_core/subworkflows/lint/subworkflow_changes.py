"""
Check whether the content of a subworkflow has changed compared to the original repository
"""

import shutil
import tempfile
from pathlib import Path

from git.exc import GitCommandError

from nf_core.components.components_differ import ComponentsDiffer
from nf_core.modules.modules_repo import ModulesRepoUnavailableError


def subworkflow_changes(subworkflow_lint_object, subworkflow):
    """
    Checks whether installed nf-core subworkflow have changed compared to the
    original repository

    Downloads the ``main.nf`` and ``meta.yml`` files for every subworkflow
    and compares them to the local copies

    If the subworkflow has a commit SHA entry in the ``modules.json``, the file content is
    compared against the files in the remote at this SHA.

    Only runs when linting a pipeline, not the modules repository

    The following checks are performed:

    subworkflow_patch
    ^^^^^^^^^^^^^^^^^

    If the subworkflow is patched, the patch must apply
    cleanly in reverse against the remote version.

    check_local_copy
    ^^^^^^^^^^^^^^^^

    Each subworkflow file must be identical to the
    corresponding file in the remote repository at the pinned commit SHA.
    """
    if not subworkflow.main_nf.is_file():
        subworkflow.failed.append(
            ("subworkflow_changes", "check_local_copy", "Installed subworkflow is missing main.nf", subworkflow.main_nf)
        )
        return

    if subworkflow.is_patched:
        # If the subworkflow is patched, we need to apply
        # the patch in reverse before comparing with the remote
        tempdir_parent = Path(tempfile.mkdtemp())
        tempdir = tempdir_parent / "tmp_subworkflow_dir"
        shutil.copytree(subworkflow.component_dir, tempdir)
        try:
            new_lines = ComponentsDiffer.try_apply_patch(
                subworkflow.component_type,
                subworkflow.component_name,
                subworkflow.org,
                subworkflow.patch_path,
                tempdir,
                reverse=True,
            )
            for file, lines in new_lines.items():
                with open(tempdir / file, "w") as fh:
                    fh.writelines(lines)
            subworkflow.passed.append(
                (
                    "subworkflow_changes",
                    "subworkflow_patch",
                    "Subworkflow patch can be cleanly applied",
                    subworkflow.component_dir,
                )
            )
        except LookupError:
            subworkflow.failed.append(
                (
                    "subworkflow_changes",
                    "subworkflow_patch",
                    "Subworkflow patch cannot be cleanly applied",
                    subworkflow.component_dir,
                )
            )
            return
    else:
        tempdir = subworkflow.component_dir
    subworkflow.branch = subworkflow_lint_object.modules_json.get_component_branch(
        "subworkflows", subworkflow.component_name, subworkflow.repo_url, subworkflow.org
    )
    try:
        modules_repo = subworkflow_lint_object.get_lint_repo(subworkflow.repo_url, subworkflow.branch)
        comparisons = modules_repo.component_files_identical(
            subworkflow.component_name, tempdir, subworkflow.git_sha, "subworkflows"
        )
    except (ModulesRepoUnavailableError, GitCommandError) as e:
        subworkflow.warned.append(
            (
                "subworkflow_changes",
                "check_local_copy",
                f"Could not compare subworkflow with the remote: {e}",
                subworkflow.component_dir,
            )
        )
        return

    for f, same in comparisons.items():
        if same:
            subworkflow.passed.append(
                (
                    "subworkflow_changes",
                    "check_local_copy",
                    "Local copy of subworkflow up to date",
                    Path(subworkflow.component_dir, f),
                )
            )
        else:
            subworkflow.failed.append(
                (
                    "subworkflow_changes",
                    "check_local_copy",
                    "Local copy of subworkflow does not match remote",
                    Path(subworkflow.component_dir, f),
                )
            )
