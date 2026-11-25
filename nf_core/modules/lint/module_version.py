"""
Verify that a module has a correct entry in the modules.json file
"""

import logging
from pathlib import Path

from git.exc import GitCommandError

import nf_core.modules.lint
from nf_core.modules.modules_repo import ModulesRepoUnavailableError
from nf_core.modules.modules_utils import NFCoreComponent

log = logging.getLogger(__name__)


def module_version(module_lint_object: "nf_core.modules.lint.ModuleLint", module: "NFCoreComponent"):
    """
    Verifies that the module has a version specified in the ``modules.json`` file

    It checks whether the module has an entry in the ``modules.json`` file
    containing a commit SHA. If that is true, it verifies that there are no
    newer version of the module available.

    The following checks are performed:

    git_sha
    ^^^^^^^

    The module must have a ``git_sha`` entry in ``modules.json``.

    module_version
    ^^^^^^^^^^^^^^

    The module version must match the latest commit in the
    remote repository. A warning is issued if a newer version is available.
    """
    assert module_lint_object.modules_json is not None  # mypy
    assert module.repo_url is not None  # mypy
    modules_json_path = Path(module_lint_object.directory, "modules.json")
    # Verify that a git_sha exists in the `modules.json` file for this module
    version = module_lint_object.modules_json.get_module_version(module.component_name, module.repo_url, module.org)
    if version is None:
        module.failed.append(("module_version", "git_sha", "No git_sha entry in `modules.json`", modules_json_path))
        return

    module.git_sha = version
    module.passed.append(("module_version", "git_sha", "Found git_sha entry in `modules.json`", modules_json_path))

    module.branch = module_lint_object.modules_json.get_component_branch(
        "modules", module.component_name, module.repo_url, module.org
    )
    try:
        modules_repo = module_lint_object.get_lint_repo(module.repo_url, module.branch)
        latest = next(iter(modules_repo.get_component_git_log(module.component_name, "modules")), None)
    except (ModulesRepoUnavailableError, GitCommandError, UserWarning) as e:
        module.warned.append(
            ("module_version", "module_version", f"Could not check module version: {e}", module.component_dir)
        )
        return

    if latest is None:
        module.warned.append(
            ("module_version", "module_version", "No git history found for module", module.component_dir)
        )
    elif version == latest["git_sha"]:
        message = "Module matches the cached version" if module_lint_object.no_pull else "Module is the latest version"
        module.passed.append(("module_version", "module_version", message, module.component_dir))
    else:
        module.warned.append(("module_version", "module_version", "New version available", module.component_dir))
