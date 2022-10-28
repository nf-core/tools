import glob
import json
import logging
import os
import re

import jinja2
import questionary
import rich

import nf_core.modules.modules_utils
import nf_core.utils
from nf_core.components.components_utils import prompt_component_version_sha
from nf_core.modules.modules_repo import NF_CORE_MODULES_NAME

log = logging.getLogger(__name__)


def verify_sha(modules_repo, prompt, sha):
    """
    Verify that 'sha' and 'prompt' arguments are not provided together.
    Verify that the provided SHA exists in the repo.

    Arguments:
        modules_repo (ModulesRepo): ModulesRepo object
        prompt (bool):              prompt asking for SHA
        sha (str):                  provided sha
    """
    if prompt and sha is not None:
        log.error("Cannot use '--sha' and '--prompt' at the same time!")
        return False

    if sha:
        if not modules_repo.sha_exists_on_branch(sha):
            log.error(f"Commit SHA '{sha}' doesn't exist in '{modules_repo.remote_url}'")
            return False

    return True


def collect_and_verify_name(component_type, component, modules_repo):
    """
    Collect component name.
    Check that the supplied name is an available module/subworkflow.
    """
    if component is None:
        component = questionary.autocomplete(
            f"{'Tool' if component_type == 'modules' else 'Subworkflow'} name:",
            choices=modules_repo.get_avail_components(component_type),
            style=nf_core.utils.nfcore_question_style,
        ).unsafe_ask()

    # Check that the supplied name is an available module/subworkflow
    if component and component not in modules_repo.get_avail_components(component_type):
        log.error(f"{component_type[:-1].title()} '{component}' not found in list of available {component_type}.")
        log.info(f"Use the command 'nf-core {component_type} list' to view available software")
        return False

    if not modules_repo.component_exists(component, component_type):
        warn_msg = f"{component_type[:-1].title()} '{component}' not found in remote '{modules_repo.remote_url}' ({modules_repo.branch})"
        log.warning(warn_msg)
        return False

    return component


def check_component_installed(component_type, component, current_version, component_dir, modules_repo, force):
    """
    Check that the module/subworkflow is not already installed
    """
    if (current_version is not None and os.path.exists(component_dir)) and not force:
        log.info(f"{component_type[:-1].title()} is already installed.")

        message = "?" if component_type == "modules" else " of this subworkflow and all it's imported modules?"
        force = questionary.confirm(
            f"{component_type[:-1].title()} {component} is already installed. \nDo you want to force the reinstallation{message}",
            style=nf_core.utils.nfcore_question_style,
            default=False,
        ).unsafe_ask()

        if not force:
            repo_flag = "" if modules_repo.repo_path == NF_CORE_MODULES_NAME else f"-g {modules_repo.remote_url} "
            branch_flag = "" if modules_repo.branch == "master" else f"-b {modules_repo.branch} "

            log.info(
                f"To update '{component}' run 'nf-core {component_type} {repo_flag}{branch_flag}update {component}'. To force reinstallation use '--force'"
            )
            return False

    return True


def get_version(component, component_type, sha, prompt, current_version, modules_repo):
    """
    Get the version to install
    """
    if sha:
        version = sha
    elif prompt:
        try:
            version = nf_core.modules.modules_utils.prompt_component_version_sha(
                component,
                component_type,
                installed_sha=current_version,
                modules_repo=modules_repo,
            )
        except SystemError as e:
            log.error(e)
            return False
    else:
        # Fetch the latest commit for the module
        version = modules_repo.get_latest_component_version(component, component_type)
    return version


def clean_modules_json(component, component_type, modules_repo, modules_json):
    """
    Remove installed version of module/subworkflow
    """
    for repo_url, repo_content in modules_json.modules_json["repos"].items():
        for dir, dir_components in repo_content[component_type].items():
            for name, _ in dir_components.items():
                if name == component and dir == modules_repo.repo_path:
                    repo_to_remove = repo_url
                    log.info(
                        f"Removing {component_type[:-1]} '{modules_repo.repo_path}/{component}' from repo '{repo_to_remove}' from modules.json"
                    )
                    modules_json.remove_entry(component, repo_to_remove, modules_repo.repo_path)
                    break
