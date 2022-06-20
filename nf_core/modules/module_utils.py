import datetime
import glob
import json
import logging
import os
import urllib
from sys import modules

import git
import questionary
import rich
from pyrsistent import m

import nf_core.utils

from .modules_repo import NF_CORE_MODULES_NAME, NF_CORE_MODULES_REMOTE, ModulesRepo
from .nfcore_module import NFCoreModule

log = logging.getLogger(__name__)


class ModuleException(Exception):
    """Exception raised when there was an error with module commands"""

    pass


def dir_tree_uncovered(modules_dir, repos):
    """
    Does a BFS of the modules directory of a pipeline and rapports any directories
    that are not found in the list of repos
    """
    # Initialise the FIFO queue. Note that we assume the directory to be correctly
    # configured, i.e. no files etc.
    fifo = [os.path.join(modules_dir, subdir) for subdir in os.listdir(modules_dir) if subdir != "local"]
    depth = 1
    dirs_not_covered = []
    while len(fifo) > 0:
        temp_queue = []
        repos_at_level = {os.path.join(*os.path.split(repo)[:depth]): len(os.path.split(repo)) for repo in repos}
        for dir in fifo:
            rel_dir = os.path.relpath(dir, modules_dir)
            if rel_dir in repos_at_level.keys():
                # Go the next depth if this directory is not one of the repos
                if depth < repos_at_level[rel_dir]:
                    temp_queue.extend([os.path.join(dir, subdir) for subdir in os.listdir(dir)])
            else:
                # Otherwise add the directory to the ones not covered
                dirs_not_covered.append(dir)
        fifo = temp_queue
        depth += 1
    return dirs_not_covered


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


def get_pipeline_module_repositories(modules_dir):
    """
    Finds all module repositories in the modules directory. Ignores the local modules.
    Args:
        modules_dir (str): base directory for the module files
    Returns
        repos [ (str, str) ]: List of tuples of repo name and repo remote URL
    """
    # Check if there are any nf-core modules installed
    if os.path.exists(os.path.join(modules_dir, NF_CORE_MODULES_NAME)):
        repos = [(NF_CORE_MODULES_NAME, NF_CORE_MODULES_REMOTE)]
    else:
        repos = []
    # Check if there are any untracked repositories
    dirs_not_covered = dir_tree_uncovered(modules_dir, [name for name, _ in repos])
    if len(dirs_not_covered) > 0:
        log.info("Found custom module repositories when creating 'modules.json'")
        # Loop until all directories in the base directory are covered by a remote
        while len(dirs_not_covered) > 0:
            log.info(
                "The following director{s} in the modules directory are untracked: '{l}'".format(
                    s="ies" if len(dirs_not_covered) > 0 else "y", l="', '".join(dirs_not_covered)
                )
            )
            nrepo_remote = questionary.text(
                "Please provide a URL for for one of the repos contained in the untracked directories"
            ).unsafe_ask()
            # Verify that the remote exists
            while True:
                try:
                    git.Git().ls_remote(nrepo_remote)
                    break
                except git.exc.GitCommandError:
                    nrepo_remote = questionary.text(
                        "The provided remote does not seem to exist, please provide a new remote."
                    ).unsafe_ask()

            # Verify that there is a directory corresponding the remote
            nrepo_name = path_from_remote(nrepo_remote)
            if not os.path.exists(os.path.join(modules_dir, nrepo_name)):
                log.info(
                    "The provided remote does not seem to correspond to a local directory. "
                    "The directory structure should be the same as in the remote"
                )
                dir_name = questionary.text(
                    "Please provide the correct directory, it will be renamed. If left empty, the remote will be ignored"
                ).unsafe_ask()
                if dir_name:
                    os.rename(os.path.join(modules_dir, dir_name), os.path.join(modules_dir, nrepo_name))
                else:
                    continue
            repos.append((nrepo_name, nrepo_remote))
            dirs_not_covered = dir_tree_uncovered(modules_dir, [name for name, _ in repos])
    return repos


def create_modules_json(pipeline_dir):
    """
    Create the modules.json files

    Args:
        pipeline_dir (str): The directory where the `modules.json` should be created
    """
    pipeline_config = nf_core.utils.fetch_wf_config(pipeline_dir)
    pipeline_name = pipeline_config.get("manifest.name", "")
    pipeline_url = pipeline_config.get("manifest.homePage", "")
    modules_json = {"name": pipeline_name.strip("'"), "homePage": pipeline_url.strip("'"), "repos": dict()}
    modules_dir = f"{pipeline_dir}/modules"

    if not os.path.exists(modules_dir):
        raise UserWarning("Can't find a ./modules directory. Is this a DSL2 pipeline?")

    repos = get_pipeline_module_repositories(modules_dir)

    # Get all module names in the repos
    repo_module_names = [
        (
            repo_name,
            [
                os.path.relpath(dir_name, os.path.join(modules_dir, repo_name))
                for dir_name, _, file_names in os.walk(os.path.join(modules_dir, repo_name))
                if "main.nf" in file_names
            ],
            repo_remote,
        )
        for repo_name, repo_remote in repos
    ]
    progress_bar = rich.progress.Progress(
        "[bold blue]{task.description}",
        rich.progress.BarColumn(bar_width=None),
        "[magenta]{task.completed} of {task.total}[reset] » [bold yellow]{task.fields[test_name]}",
        transient=True,
    )
    with progress_bar:
        n_total_modules = sum(len(modules) for _, modules, _ in repo_module_names)
        file_progress = progress_bar.add_task(
            "Creating 'modules.json' file", total=n_total_modules, test_name="module.json"
        )
        for repo_name, module_names, remote in sorted(repo_module_names):
            try:
                # Create a ModulesRepo object without progress bar to not conflict with the other one
                modules_repo = ModulesRepo(remote_url=remote, no_progress=True)
            except LookupError as e:
                raise UserWarning(e)

            repo_path = os.path.join(modules_dir, repo_name)
            modules_json["repos"][repo_name] = dict()
            modules_json["repos"][repo_name]["git_url"] = remote
            modules_json["repos"][repo_name]["modules"] = dict()
            for module_name in sorted(module_names):
                module_path = os.path.join(repo_path, module_name)
                progress_bar.update(file_progress, advance=1, test_name=f"{repo_name}/{module_name}")
                correct_commit_sha = find_correct_commit_sha(module_name, module_path, modules_repo)

                modules_json["repos"][repo_name]["modules"][module_name] = {"git_sha": correct_commit_sha}

    modules_json_path = os.path.join(pipeline_dir, "modules.json")
    with open(modules_json_path, "w") as fh:
        json.dump(modules_json, fh, indent=4)
        fh.write("\n")


def find_correct_commit_sha(module_name, module_path, modules_repo):
    """
    Returns the SHA for the latest commit where the local files are identical to the remote files
    Args:
        module_name (str): Name of module
        module_path (str): Path to module in local repo
        module_repo (str): Remote repo for module
    Returns:
        commit_sha (str): The latest commit SHA where local files are identical to remote files
    """
    # Find the correct commit SHA for the local module files.
    # We iterate over the commit history for the module until we find
    # a revision that matches the file contents
    commit_shas = (commit["git_sha"] for commit in modules_repo.get_module_git_log(module_name, depth=1000))
    for commit_sha in commit_shas:
        if all(modules_repo.module_files_identical(module_name, module_path, commit_sha).values()):
            return commit_sha
    return None


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
    if dir is None or not os.path.exists(dir):
        raise UserWarning(f"Could not find directory: {dir}")

    # Try to find the root directory
    base_dir = os.path.abspath(dir)
    config_path_yml = os.path.join(base_dir, ".nf-core.yml")
    config_path_yaml = os.path.join(base_dir, ".nf-core.yaml")
    while (
        not os.path.exists(config_path_yml)
        and not os.path.exists(config_path_yaml)
        and base_dir != os.path.dirname(base_dir)
    ):
        base_dir = os.path.dirname(base_dir)
        config_path_yml = os.path.join(base_dir, ".nf-core.yml")
        config_path_yaml = os.path.join(base_dir, ".nf-core.yaml")
        # Reset dir if we found the config file (will be an absolute path)
        if os.path.exists(config_path_yml) or os.path.exists(config_path_yaml):
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
            with open(os.path.join(dir, ".nf-core.yml"), "a+") as fh:
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
