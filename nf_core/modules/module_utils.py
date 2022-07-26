import logging
import os
import urllib
from pathlib import Path

import questionary
import rich

import nf_core.utils

from .nfcore_module import NFCoreModule

log = logging.getLogger(__name__)


class ModuleException(Exception):
    """Exception raised when there was an error with module commands"""

    pass


def path_from_remote(remote_url):
    """
    Extracts the path from the remote URL
    See https://mirrors.edge.kernel.org/pub/software/scm/git/docs/git-clone.html#URLS for the possible URL patterns
    """
    # Check whether we have a https or ssh url
    if remote_url.startswith("https"):
        path = urllib.parse.urlparse(remote_url)
        path = path.path
        # Remove the intial '/'
        path = path[1:]
        path = os.path.splitext(path)[0]
    else:
        # Remove the initial `git@``
        path = remote_url.split("@")
        path = path[-1] if len(path) > 1 else path[0]
        path = urllib.parse.urlparse(path)
        path = path.path
        path = os.path.splitext(path)[0]
    return path


def get_installed_modules(dir, repo_type="modules"):
    """
    Make a list of all modules installed in this repository

    Returns a tuple of two lists, one for local modules
    and one for nf-core modules. The local modules are represented
    as direct filepaths to the module '.nf' file.
    Nf-core module are returned as file paths to the module directories.
    In case the module contains several tools, one path to each tool directory
    is returned.

    returns (local_modules, nfcore_modules)
    """
    # initialize lists
    local_modules = []
    nfcore_modules = []
    local_modules_dir = None
    nfcore_modules_dir = os.path.join(dir, "modules", "nf-core", "modules")

    # Get local modules
    if repo_type == "pipeline":
        local_modules_dir = os.path.join(dir, "modules", "local", "process")

        # Filter local modules
        if os.path.exists(local_modules_dir):
            local_modules = os.listdir(local_modules_dir)
            local_modules = sorted([x for x in local_modules if x.endswith(".nf")])

    # nf-core/modules
    if repo_type == "modules":
        nfcore_modules_dir = os.path.join(dir, "modules")

    # Get nf-core modules
    if os.path.exists(nfcore_modules_dir):
        for m in sorted([m for m in os.listdir(nfcore_modules_dir) if not m == "lib"]):
            if not os.path.isdir(os.path.join(nfcore_modules_dir, m)):
                raise ModuleException(
                    f"File found in '{nfcore_modules_dir}': '{m}'! This directory should only contain module directories."
                )
            m_content = os.listdir(os.path.join(nfcore_modules_dir, m))
            # Not a module, but contains sub-modules
            if not "main.nf" in m_content:
                for tool in m_content:
                    nfcore_modules.append(os.path.join(m, tool))
            else:
                nfcore_modules.append(m)

    # Make full (relative) file paths and create NFCoreModule objects
    local_modules = [os.path.join(local_modules_dir, m) for m in local_modules]
    nfcore_modules = [
        NFCoreModule(os.path.join(nfcore_modules_dir, m), repo_type=repo_type, base_dir=dir) for m in nfcore_modules
    ]

    return local_modules, nfcore_modules


def get_repo_type(dir, repo_type=None, use_prompt=True):
    """
    Determine whether this is a pipeline repository or a clone of
    nf-core/modules
    """
    # Verify that the pipeline dir exists
    if dir is None:
        raise UserWarning("A directory must be supplied.")

    dir = Path(dir)
    if not dir.exists():
        raise UserWarning(f"Could not find directory: {dir}")

    # Try to find the root directory
    base_dir = dir.absolute()
    config_path_yml = base_dir / ".nf-core.yml"
    config_path_yaml = base_dir / ".nf-core.yaml"
    while not config_path_yml.exists() and not config_path_yaml.exists() and base_dir != base_dir.parent:
        base_dir = base_dir.parent
        config_path_yml = base_dir / ".nf-core.yml"
        config_path_yaml = base_dir / ".nf-core.yaml"
        # Reset dir if we found the config file (will be an absolute path)
        if config_path_yml.exists() or config_path_yaml.exists():
            dir = base_dir

    # Figure out the repository type from the .nf-core.yml config file if we can
    tools_config = nf_core.utils.load_tools_config(dir)
    repo_type = tools_config.get("repository_type", None)

    # If not set, prompt the user
    if not repo_type and use_prompt:
        log.warning("Can't find a '.nf-core.yml' file that defines 'repository_type'")
        repo_type = questionary.select(
            "Is this repository an nf-core pipeline or a fork of nf-core/modules?",
            choices=[
                {"name": "Pipeline", "value": "pipeline"},
                {"name": "nf-core/modules", "value": "modules"},
            ],
            style=nf_core.utils.nfcore_question_style,
        ).unsafe_ask()

        # Save the choice in the config file
        log.info("To avoid this prompt in the future, add the 'repository_type' key to a root '.nf-core.yml' file.")
        if rich.prompt.Confirm.ask("[bold][blue]?[/] Would you like me to add this config now?", default=True):
            with open((dir / ".nf-core.yml"), "a+") as fh:
                fh.write(f"repository_type: {repo_type}\n")
                log.info("Config added to '.nf-core.yml'")

    # Not set and not allowed to ask
    elif not repo_type:
        raise UserWarning("Repository type could not be established")

    # Check if it's a valid answer
    if not repo_type in ["pipeline", "modules"]:
        raise UserWarning(f"Invalid repository type: '{repo_type}'")

    # It was set on the command line, return what we were given
    return [dir, repo_type]


def prompt_module_version_sha(module, modules_repo, installed_sha=None):
    """
    Creates an interactive questionary prompt for selecting the module version
    Args:
        module (str): Module name
        modules_repo (ModulesRepo): Modules repo the module originate in
        installed_sha (str): Optional extra argument to highlight the current installed version

    Returns:
        git_sha (str): The selected version of the module
    """
    older_commits_choice = questionary.Choice(
        title=[("fg:ansiyellow", "older commits"), ("class:choice-default", "")], value=""
    )
    git_sha = ""
    page_nbr = 1

    all_commits = modules_repo.get_module_git_log(module)
    next_page_commits = [next(all_commits, None) for _ in range(10)]
    next_page_commits = [commit for commit in next_page_commits if commit is not None]

    while git_sha == "":
        commits = next_page_commits
        next_page_commits = [next(all_commits, None) for _ in range(10)]
        next_page_commits = [commit for commit in next_page_commits if commit is not None]
        if all(commit is None for commit in next_page_commits):
            next_page_commits = None

        choices = []
        for title, sha in map(lambda commit: (commit["trunc_message"], commit["git_sha"]), commits):
            display_color = "fg:ansiblue" if sha != installed_sha else "fg:ansired"
            message = f"{title} {sha}"
            if installed_sha == sha:
                message += " (installed version)"
            commit_display = [(display_color, message), ("class:choice-default", "")]
            choices.append(questionary.Choice(title=commit_display, value=sha))
        if next_page_commits is not None:
            choices += [older_commits_choice]
        git_sha = questionary.select(
            f"Select '{module}' commit:", choices=choices, style=nf_core.utils.nfcore_question_style
        ).unsafe_ask()
        page_nbr += 1
    return git_sha
